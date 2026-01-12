# fixtex
Uses LLMs to fix bibliography entries, because doing so manually is annoying.

## Overview

FixTeX is a Python tool that automatically finds, verifies, and reformats BibTeX entries using:
- **Google Scholar**: To find and verify citations
- **Selenium**: To automate web scraping and select the most reputable sources
- **OpenRouter API**: To reformat citations using state-of-the-art LLMs

## Features

- Automatically searches for each BibTeX entry on Google Scholar
- Clicks "All N versions" to compare different versions of papers
- Selects the most reputable source (e.g., ICML over arXiv)
- Uses LLMs to reformat and standardize BibTeX entries
- Preserves original entry IDs while improving citation quality

## Installation

1. Clone the repository:
```bash
git clone https://github.com/MiniXC/fixtex.git
cd fixtex
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenRouter API key:
```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

## Usage

Basic usage:
```bash
python fixtex.py input.bib
```

This will create `input_fixed.bib` with the reformatted entries.

### Options

```bash
python fixtex.py input.bib -o output.bib        # Specify output file
python fixtex.py input.bib -s ieee              # Use IEEE citation style
python fixtex.py input.bib -k YOUR_API_KEY      # Provide API key directly
python fixtex.py input.bib --no-headless        # Show browser (for debugging)
```

### Example

```bash
python fixtex.py example.bib
```

## Requirements

- Python 3.7+
- Chrome/Chromium browser (for Selenium)
- OpenRouter API key ([Get one here](https://openrouter.ai/))

## How It Works

1. **Parse**: Reads the input BibTeX file
2. **Search**: For each entry, searches Google Scholar using the title or author+year
3. **Select**: Clicks "All versions" and selects the most reputable source based on:
   - Conference rankings (ICML, NeurIPS, CVPR, etc.)
   - Journal rankings (ACM, IEEE, Springer, etc.)
   - Preprint servers (arXiv) as fallback
4. **Extract**: Gets the BibTeX citation from the selected source
5. **Reformat**: Uses an LLM (via OpenRouter) to clean and standardize the entry
6. **Output**: Writes all entries to a new BibTeX file

## Source Reputation Ranking

FixTeX ranks sources in the following order (from most to least reputable):
- Top-tier conferences: ACM, IEEE, NeurIPS, ICML, ICLR, CVPR (90-100)
- Major conferences: AAAI, IJCAI, ACL, EMNLP (85-90)
- Journals: JMLR, PMLR (85-90)
- Preprints: arXiv (50)
- PDFs: Generic PDFs (30)

## License

MIT License
