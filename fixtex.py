#!/usr/bin/env python3
"""
FixTeX - Automatically fix and reformat BibTeX entries using Google Scholar and LLMs.

This script takes a .bib file and citation style as input, searches for each entry
on Google Scholar, selects the most reputable version, and uses an LLM to reformat
the citation.
"""

import argparse
import os
import sys
import time
from typing import List, Dict, Optional
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
import requests


# Load environment variables
load_dotenv()


class ScholarScraper:
    """Scrapes Google Scholar for BibTeX entries."""
    
    def __init__(self, headless: bool = True, llm_reformatter=None):
        """Initialize the scraper with Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.llm_reformatter = llm_reformatter
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()
    
    def search_entry(self, entry: Dict) -> Optional[str]:
        """
        Search for a BibTeX entry on Google Scholar and return the best citation.
        
        Args:
            entry: BibTeX entry dictionary
            
        Returns:
            BibTeX string of the best citation found, or None if not found
        """
        # Build search query from entry
        query = self._build_query(entry)
        if not query:
            print(f"Warning: Could not build query for entry {entry.get('ID', 'unknown')}")
            return None
        
        print(f"Searching for: {query}")
        
        try:
            # Search on Google Scholar
            self.driver.get(f"https://scholar.google.com/scholar?q={query}")
            time.sleep(2)  # Wait for page load
            
            # Find the first result
            results = self.driver.find_elements(By.CSS_SELECTOR, '.gs_ri')
            if not results:
                print(f"No results found for: {query}")
                return None
            
            first_result = results[0]
            
            # Try to find and click "Cited by" or "All X versions" link
            versions_link = None
            try:
                # Look for "All X versions" link
                links = first_result.find_elements(By.CSS_SELECTOR, '.gs_fl a')
                for link in links:
                    if 'version' in link.text.lower():
                        versions_link = link
                        break
            except NoSuchElementException:
                pass
            
            # If we found versions link, click it to see all versions
            if versions_link:
                print(f"Found versions link: {versions_link.text}")
                versions_link.click()
                time.sleep(2)
                
                # Now get all versions and select the most reputable one
                best_result = self._select_best_version()
            else:
                # Use the first result
                best_result = first_result
            
            # Get the citation for the best result
            citation = self._get_citation(best_result)
            return citation
            
        except Exception as e:
            print(f"Error searching for entry: {e}")
            return None
    
    def _build_query(self, entry: Dict) -> Optional[str]:
        """Build a search query from a BibTeX entry."""
        # Try to use title first
        if 'title' in entry:
            title = entry['title'].strip('{}')
            return title
        
        # Fallback to author + year
        parts = []
        if 'author' in entry:
            # Get first author
            author = entry['author'].split(' and ')[0]
            parts.append(author)
        if 'year' in entry:
            parts.append(entry['year'])
        
        return ' '.join(parts) if parts else None
    
    def _select_best_version(self) -> object:
        """
        From a versions page, select the most reputable version using LLM.
        
        Returns:
            Selenium WebElement of the best result
        """
        results = self.driver.find_elements(By.CSS_SELECTOR, '.gs_ri')
        if not results:
            return None
        
        if len(results) == 1:
            print("Only one version found, using it")
            return results[0]
        
        # If we have an LLM reformatter, use it to select the best version
        if self.llm_reformatter:
            best_result = self._llm_select_best_version(results)
            if best_result:
                return best_result
        
        # Fallback to first result if LLM selection fails
        print("Using first result as fallback")
        return results[0]
    
    def _llm_select_best_version(self, results: List) -> Optional[object]:
        """
        Use LLM to select the most reputable version from a list of results.
        
        Args:
            results: List of Selenium WebElements representing search results
            
        Returns:
            The best result WebElement, or None if selection fails
        """
        try:
            # Extract information about each version
            versions_info = []
            for i, result in enumerate(results[:10]):  # Limit to first 10 versions
                try:
                    # Get title
                    title_elem = result.find_element(By.CSS_SELECTOR, '.gs_rt')
                    title = title_elem.text
                    
                    # Get publication info (venue, year, etc.)
                    info_elem = result.find_element(By.CSS_SELECTOR, '.gs_a')
                    info = info_elem.text
                    
                    # Get snippet/abstract if available
                    snippet = ""
                    try:
                        snippet_elem = result.find_element(By.CSS_SELECTOR, '.gs_rs')
                        snippet = snippet_elem.text
                    except:
                        pass
                    
                    versions_info.append({
                        'index': i,
                        'title': title,
                        'info': info,
                        'snippet': snippet
                    })
                except Exception as e:
                    print(f"Warning: Could not extract info for version {i}: {e}")
                    continue
            
            if not versions_info:
                return None
            
            # Ask LLM to select the best version
            print(f"Asking LLM to select best version from {len(versions_info)} options...")
            best_index = self.llm_reformatter.select_best_version(versions_info)
            
            if best_index is not None and 0 <= best_index < len(results):
                print(f"LLM selected version {best_index}")
                return results[best_index]
            else:
                print(f"LLM returned invalid index: {best_index}, using first result")
                return results[0]
                
        except Exception as e:
            print(f"Error in LLM version selection: {e}")
            return None
    
    def _get_citation(self, result) -> Optional[str]:
        """
        Get BibTeX citation for a result.
        
        Args:
            result: Selenium WebElement of the search result
            
        Returns:
            BibTeX citation string or None
        """
        try:
            # Find the cite button
            cite_button = result.find_element(By.CSS_SELECTOR, '.gs_or_cit')
            cite_button.click()
            time.sleep(1)
            
            # Click on BibTeX link
            bibtex_link = self.wait.until(
                EC.presence_of_element_located((By.LINK_TEXT, 'BibTeX'))
            )
            bibtex_link.click()
            time.sleep(1)
            
            # Get the BibTeX content
            bibtex_content = self.driver.find_element(By.TAG_NAME, 'pre').text
            
            # Go back to search results
            self.driver.back()
            time.sleep(1)
            
            return bibtex_content
            
        except Exception as e:
            print(f"Error getting citation: {e}")
            return None


class LLMReformatter:
    """Uses OpenRouter API to reformat BibTeX entries."""
    
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        """
        Initialize the LLM reformatter.
        
        Args:
            api_key: OpenRouter API key
            model: Model to use for reformatting
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def reformat(self, bibtex: str, style: str = "standard") -> Optional[str]:
        """
        Reformat a BibTeX entry using an LLM.
        
        Args:
            bibtex: BibTeX entry to reformat
            style: Citation style to use
            
        Returns:
            Reformatted BibTeX string or None on error
        """
        prompt = self._build_prompt(bibtex, style)
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the reformatted BibTeX from the response
            content = result['choices'][0]['message']['content']
            
            # Extract BibTeX from markdown code blocks if present
            if '```' in content:
                # Find content between ```bibtex or ``` and ```
                lines = content.split('\n')
                in_code_block = False
                bibtex_lines = []
                for line in lines:
                    if line.strip().startswith('```'):
                        if in_code_block:
                            break
                        in_code_block = True
                        continue
                    if in_code_block:
                        bibtex_lines.append(line)
                content = '\n'.join(bibtex_lines)
            
            return content.strip()
            
        except Exception as e:
            print(f"Error reformatting with LLM: {e}")
            return None
    
    def _build_prompt(self, bibtex: str, style: str) -> str:
        """Build the prompt for the LLM."""
        return f"""Please reformat the following BibTeX entry according to {style} style.
Ensure the entry is properly formatted, has consistent capitalization, and includes all necessary fields.
Remove any duplicate or redundant information.
Return only the reformatted BibTeX entry, without any additional explanation.

BibTeX entry:
{bibtex}

Reformatted BibTeX entry:"""
    
    def select_best_version(self, versions: List[Dict]) -> Optional[int]:
        """
        Use LLM to select the most reputable version from a list of versions.
        
        Args:
            versions: List of version dictionaries with 'index', 'title', 'info', 'snippet'
            
        Returns:
            Index of the best version, or None on error
        """
        prompt = self._build_selection_prompt(versions)
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the selected index from the response
            content = result['choices'][0]['message']['content'].strip()
            
            # Try to extract the number from the response
            # Look for patterns like "Version 0", "0", "index 0", etc.
            import re
            numbers = re.findall(r'\b(\d+)\b', content)
            if numbers:
                selected_index = int(numbers[0])
                return selected_index
            
            return None
            
        except Exception as e:
            print(f"Error selecting best version with LLM: {e}")
            return None
    
    def _build_selection_prompt(self, versions: List[Dict]) -> str:
        """Build the prompt for version selection."""
        versions_text = []
        for v in versions:
            versions_text.append(f"""Version {v['index']}:
Title: {v['title']}
Publication Info: {v['info']}
Snippet: {v['snippet'][:200] if v['snippet'] else 'N/A'}
""")
        
        versions_str = "\n---\n".join(versions_text)
        
        return f"""You are helping to select the most reputable publication version from multiple sources.
Consider the following factors in order of importance:
1. Peer-reviewed conference/journal publications are most reputable (e.g., ICML, NeurIPS, CVPR, ACL, IEEE, ACM)
2. Workshop papers and published proceedings are moderately reputable
3. Preprint servers (arXiv, bioRxiv) are less reputable than peer-reviewed venues
4. PDFs from personal websites or unknown sources are least reputable

Below are the available versions of a paper. Please select the MOST REPUTABLE version.

{versions_str}

Please respond with ONLY the number (index) of the most reputable version. For example, if Version 2 is most reputable, respond with just "2"."""


def parse_bibtex_file(filepath: str) -> List[Dict]:
    """
    Parse a BibTeX file and return a list of entries.
    
    Args:
        filepath: Path to the .bib file
        
    Returns:
        List of BibTeX entry dictionaries
    """
    with open(filepath, 'r', encoding='utf-8') as bibfile:
        parser = BibTexParser()
        parser.ignore_nonstandard_types = False
        bib_database = bibtexparser.load(bibfile, parser=parser)
        return bib_database.entries


def write_bibtex_file(filepath: str, entries: List[Dict]):
    """
    Write BibTeX entries to a file.
    
    Args:
        filepath: Path to the output .bib file
        entries: List of BibTeX entry dictionaries
    """
    db = bibtexparser.bibdatabase.BibDatabase()
    db.entries = entries
    
    writer = BibTexWriter()
    writer.indent = '  '
    writer.order_entries_by = None
    
    with open(filepath, 'w', encoding='utf-8') as bibfile:
        bibfile.write(writer.write(db))


def process_bibtex(input_file: str, output_file: str, style: str = "standard", 
                   api_key: Optional[str] = None, headless: bool = True):
    """
    Process a BibTeX file: search for entries, select best versions, and reformat.
    
    Args:
        input_file: Path to input .bib file
        output_file: Path to output .bib file
        style: Citation style to use
        api_key: OpenRouter API key (if None, reads from environment)
        headless: Whether to run browser in headless mode
    """
    # Get API key
    if api_key is None:
        api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment or provided as argument")
        sys.exit(1)
    
    # Parse input file
    print(f"Reading BibTeX file: {input_file}")
    entries = parse_bibtex_file(input_file)
    print(f"Found {len(entries)} entries")
    
    # Initialize scraper and reformatter
    reformatter = LLMReformatter(api_key)
    fixed_entries = []
    
    with ScholarScraper(headless=headless, llm_reformatter=reformatter) as scraper:
        for i, entry in enumerate(entries, 1):
            entry_id = entry.get('ID', 'unknown')
            print(f"\n[{i}/{len(entries)}] Processing entry: {entry_id}")
            
            # Search for the entry on Google Scholar
            citation = scraper.search_entry(entry)
            
            if citation:
                print(f"Found citation for {entry_id}")
                
                # Reformat with LLM
                print(f"Reformatting with LLM...")
                reformatted = reformatter.reformat(citation, style)
                
                if reformatted:
                    # Parse the reformatted BibTeX
                    try:
                        parser = BibTexParser()
                        parsed = bibtexparser.loads(reformatted, parser=parser)
                        if parsed.entries:
                            # Preserve the original entry ID if possible
                            new_entry = parsed.entries[0]
                            new_entry['ID'] = entry_id
                            fixed_entries.append(new_entry)
                            print(f"Successfully reformatted {entry_id}")
                        else:
                            print(f"Warning: Could not parse reformatted entry for {entry_id}, using original")
                            fixed_entries.append(entry)
                    except Exception as e:
                        print(f"Error parsing reformatted entry: {e}, using original")
                        fixed_entries.append(entry)
                else:
                    print(f"Warning: Could not reformat {entry_id}, using original")
                    fixed_entries.append(entry)
            else:
                print(f"Warning: Could not find citation for {entry_id}, using original")
                fixed_entries.append(entry)
            
            # Be nice to Google Scholar
            time.sleep(3)
    
    # Write output file
    print(f"\nWriting results to: {output_file}")
    write_bibtex_file(output_file, fixed_entries)
    print(f"Done! Processed {len(fixed_entries)} entries")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Fix and reformat BibTeX entries using Google Scholar and LLMs'
    )
    parser.add_argument(
        'input',
        type=str,
        help='Input .bib file'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output .bib file (default: input_fixed.bib)'
    )
    parser.add_argument(
        '-s', '--style',
        type=str,
        default='standard',
        help='Citation style (default: standard)'
    )
    parser.add_argument(
        '-k', '--api-key',
        type=str,
        help='OpenRouter API key (default: from OPENROUTER_API_KEY env var)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in non-headless mode (visible)'
    )
    
    args = parser.parse_args()
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        input_path = Path(args.input)
        output_file = str(input_path.parent / f"{input_path.stem}_fixed.bib")
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # Process the BibTeX file
    process_bibtex(
        args.input,
        output_file,
        args.style,
        args.api_key,
        headless=not args.no_headless
    )


if __name__ == '__main__':
    main()
