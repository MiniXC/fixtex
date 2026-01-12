#!/usr/bin/env python3
"""
Simple test to verify core functionality of fixtex.
"""

import os
import sys
from pathlib import Path

# Test imports
print("Testing imports...")
try:
    import bibtexparser
    from bibtexparser.bparser import BibTexParser
    from bibtexparser.bwriter import BibTexWriter
    print("✓ bibtexparser imported successfully")
except ImportError as e:
    print(f"✗ Failed to import bibtexparser: {e}")
    sys.exit(1)

try:
    from selenium import webdriver
    print("✓ selenium imported successfully")
except ImportError as e:
    print(f"✗ Failed to import selenium: {e}")
    sys.exit(1)

try:
    import requests
    print("✓ requests imported successfully")
except ImportError as e:
    print(f"✗ Failed to import requests: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv imported successfully")
except ImportError as e:
    print(f"✗ Failed to import python-dotenv: {e}")
    sys.exit(1)

# Test BibTeX parsing
print("\nTesting BibTeX parsing...")
try:
    with open('example.bib', 'r') as f:
        parser = BibTexParser()
        parser.ignore_nonstandard_types = False
        bib = bibtexparser.load(f, parser=parser)
        print(f"✓ Successfully parsed {len(bib.entries)} entries")
        for entry in bib.entries:
            print(f"  - {entry['ID']}: {entry.get('title', 'No title')[:50]}")
except Exception as e:
    print(f"✗ Failed to parse BibTeX: {e}")
    sys.exit(1)

# Test module structure
print("\nTesting fixtex module structure...")
try:
    import fixtex
    print("✓ fixtex module imported successfully")
    
    # Check if classes exist
    assert hasattr(fixtex, 'ScholarScraper'), "ScholarScraper class not found"
    print("✓ ScholarScraper class found")
    
    assert hasattr(fixtex, 'LLMReformatter'), "LLMReformatter class not found"
    print("✓ LLMReformatter class found")
    
    assert hasattr(fixtex, 'parse_bibtex_file'), "parse_bibtex_file function not found"
    print("✓ parse_bibtex_file function found")
    
    assert hasattr(fixtex, 'write_bibtex_file'), "write_bibtex_file function not found"
    print("✓ write_bibtex_file function found")
    
    assert hasattr(fixtex, 'process_bibtex'), "process_bibtex function not found"
    print("✓ process_bibtex function found")
    
except Exception as e:
    print(f"✗ Failed to import or verify fixtex module: {e}")
    sys.exit(1)

# Test LLMReformatter initialization
print("\nTesting LLMReformatter initialization...")
try:
    reformatter = fixtex.LLMReformatter("test_key", model="test_model")
    print(f"✓ LLMReformatter initialized with API key and model")
    assert reformatter.api_key == "test_key"
    assert reformatter.model == "test_model"
    print("✓ LLMReformatter attributes set correctly")
except Exception as e:
    print(f"✗ Failed to initialize LLMReformatter: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("All basic tests passed! ✓")
print("="*50)
print("\nNote: Full integration tests require:")
print("  - Chrome/ChromeDriver (installed)")
print("  - OpenRouter API key (set OPENROUTER_API_KEY env var)")
print("  - Internet connection for Google Scholar and API")
