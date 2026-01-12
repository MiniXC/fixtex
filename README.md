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

## Configuration

### Environment Variables

Create a `.env` file in the project directory with your OpenRouter API key:

```bash
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet  # Optional, defaults to claude-3.5-sonnet
```

You can also pass the API key directly via command line:

```bash
python fixtex.py input.bib -k YOUR_API_KEY
```

### Supported Models

FixTeX works with any model available on OpenRouter. Some recommended models:

- `anthropic/claude-3.5-sonnet` (default, best quality)
- `anthropic/claude-3-haiku` (faster, lower cost)
- `openai/gpt-4` (high quality)
- `openai/gpt-3.5-turbo` (faster, lower cost)

## Troubleshooting

### Chrome/ChromeDriver Issues

If you encounter Chrome/ChromeDriver errors:

1. Ensure Chrome or Chromium is installed:
   ```bash
   google-chrome --version  # or chromium-browser --version
   ```

2. ChromeDriver should be automatically managed by Selenium 4.x

3. Try running in non-headless mode to see what's happening:
   ```bash
   python fixtex.py input.bib --no-headless
   ```

### Rate Limiting

Google Scholar may rate-limit requests. The script includes delays between requests, but if you're processing many entries:

- Consider processing in smaller batches
- The script waits 3 seconds between entries by default
- Avoid running multiple instances simultaneously

### API Errors

If you encounter OpenRouter API errors:

- Verify your API key is correct
- Check your account has sufficient credits
- Some models may have usage limits or require specific permissions

## How It Works

1. **Parse**: Reads the input BibTeX file
2. **Search**: For each entry, searches Google Scholar using the title or author+year
3. **Select**: Clicks "All versions" and uses an LLM to select the most reputable source by analyzing:
   - Publication venue (conference, journal, preprint server)
   - Peer-review status
   - Venue reputation (ICML, NeurIPS, CVPR, ACL, IEEE, ACM, etc.)
   - Publication type (full paper vs workshop vs preprint)
4. **Extract**: Gets the BibTeX citation from the selected source
5. **Reformat**: Uses an LLM (via OpenRouter) to clean and standardize the entry
6. **Output**: Writes all entries to a new BibTeX file

## LLM-Powered Source Selection

Unlike traditional tools that rely on hardcoded rules, FixTeX uses an LLM to intelligently evaluate and select the most reputable version of each paper. The LLM considers:

- **Peer-reviewed venues**: Prioritizes top-tier conferences (ICML, NeurIPS, CVPR, ACL) and journals (IEEE, ACM, Springer)
- **Publication quality**: Distinguishes between full conference papers, workshop papers, and preprints
- **Context awareness**: Understands venue reputation within specific research domains
- **Flexibility**: Adapts to new venues and publication types without code changes

This approach is more robust and maintainable than keyword matching, and can make nuanced decisions based on the full context of each publication.

## License

MIT License
