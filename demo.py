#!/usr/bin/env python3
"""
Demo script showing how to use fixtex programmatically.
"""

import fixtex

# Example: Process a BibTeX file
def demo_basic_usage():
    """Basic usage example."""
    print("=" * 60)
    print("DEMO: Basic Usage")
    print("=" * 60)
    print()
    print("Command line usage:")
    print("  python fixtex.py example.bib")
    print()
    print("This will:")
    print("  1. Read example.bib")
    print("  2. Search each entry on Google Scholar")
    print("  3. Click 'All versions' for each entry")
    print("  4. Use LLM to select the most reputable version")
    print("  5. Extract the BibTeX citation")
    print("  6. Reformat with LLM")
    print("  7. Write to example_fixed.bib")
    print()

def demo_programmatic_usage():
    """Programmatic usage example."""
    print("=" * 60)
    print("DEMO: Programmatic Usage")
    print("=" * 60)
    print()
    print("Python code:")
    print("""
import fixtex

# Initialize LLM reformatter
reformatter = fixtex.LLMReformatter(
    api_key="your_openrouter_key",
    model="anthropic/claude-3.5-sonnet"
)

# Initialize scraper with LLM support
with fixtex.ScholarScraper(headless=True, llm_reformatter=reformatter) as scraper:
    # Parse BibTeX file
    entries = fixtex.parse_bibtex_file("input.bib")
    
    fixed_entries = []
    for entry in entries:
        # Search for entry
        citation = scraper.search_entry(entry)
        
        if citation:
            # Reformat with LLM
            reformatted = reformatter.reformat(citation, style="standard")
            fixed_entries.append(reformatted)
    
    # Write output
    fixtex.write_bibtex_file("output.bib", fixed_entries)
""")
    print()

def demo_workflow():
    """Detailed workflow example."""
    print("=" * 60)
    print("DEMO: Detailed Workflow")
    print("=" * 60)
    print()
    
    # Parse example file
    print("1. Parsing example.bib...")
    entries = fixtex.parse_bibtex_file("example.bib")
    print(f"   Found {len(entries)} entries:")
    for entry in entries:
        title = entry.get('title', 'No title').strip('{}')
        print(f"   - {entry['ID']}: {title[:50]}...")
    print()
    
    print("2. For each entry, the tool will:")
    print("   a. Build search query from title/author")
    print("   b. Search Google Scholar")
    print("   c. Click 'All N versions' link")
    print("   d. Extract info for each version (title, venue, snippet)")
    print("   e. Send version info to LLM for selection")
    print("   f. LLM evaluates based on:")
    print("      - Peer-review status (conference > workshop > preprint)")
    print("      - Venue reputation (ICML, NeurIPS > arXiv)")
    print("      - Publication type")
    print("   g. Extract BibTeX from selected version")
    print("   h. Send to LLM for reformatting")
    print("   i. Add to output collection")
    print()
    
    print("3. Write all reformatted entries to output file")
    print()
    
    print("Benefits of LLM-based selection:")
    print("  ✓ No hardcoded venue rankings to maintain")
    print("  ✓ Understands context and nuance")
    print("  ✓ Adapts to new venues automatically")
    print("  ✓ Can handle complex cases (workshops vs main conference)")
    print()

def demo_advanced_options():
    """Show advanced usage options."""
    print("=" * 60)
    print("DEMO: Advanced Options")
    print("=" * 60)
    print()
    print("Custom citation style:")
    print("  python fixtex.py input.bib -s ieee")
    print()
    print("Custom output file:")
    print("  python fixtex.py input.bib -o cleaned.bib")
    print()
    print("API key from command line:")
    print("  python fixtex.py input.bib -k YOUR_API_KEY")
    print()
    print("Non-headless mode (see browser):")
    print("  python fixtex.py input.bib --no-headless")
    print()
    print("Complete example:")
    print("  python fixtex.py papers.bib -o papers_clean.bib -s acm --no-headless")
    print()

if __name__ == "__main__":
    demo_basic_usage()
    demo_programmatic_usage()
    demo_workflow()
    demo_advanced_options()
    
    print("=" * 60)
    print("To actually run fixtex, you need:")
    print("  1. OpenRouter API key (set OPENROUTER_API_KEY)")
    print("  2. Internet connection")
    print("  3. Chrome/ChromeDriver installed")
    print()
    print("Then run:")
    print("  python fixtex.py example.bib")
    print("=" * 60)
