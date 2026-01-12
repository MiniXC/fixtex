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
    
    # Source reputation ranking (higher is more reputable)
    SOURCE_REPUTATION = {
        'acm': 100,
        'ieee': 100,
        'springer': 90,
        'neurips': 95,
        'icml': 95,
        'iclr': 95,
        'cvpr': 95,
        'iccv': 95,
        'eccv': 95,
        'nips': 95,
        'aaai': 90,
        'ijcai': 90,
        'acl': 90,
        'emnlp': 90,
        'naacl': 90,
        'pmlr': 85,
        'jmlr': 90,
        'arxiv': 50,
        'pdf': 30,
    }
    
    def __init__(self, headless: bool = True):
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
        From a versions page, select the most reputable version.
        
        Returns:
            Selenium WebElement of the best result
        """
        results = self.driver.find_elements(By.CSS_SELECTOR, '.gs_ri')
        if not results:
            return None
        
        best_result = None
        best_score = -1
        
        for result in results:
            score = self._score_result(result)
            if score > best_score:
                best_score = score
                best_result = result
        
        print(f"Selected version with score: {best_score}")
        return best_result if best_result else results[0]
    
    def _score_result(self, result) -> int:
        """Score a search result based on source reputation."""
        try:
            # Get the text content of the result
            text = result.text.lower()
            
            # Check for each source in our reputation list
            max_score = 0
            for source, score in self.SOURCE_REPUTATION.items():
                if source in text:
                    max_score = max(max_score, score)
            
            return max_score
        except:
            return 0
    
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
    
    with ScholarScraper(headless=headless) as scraper:
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
