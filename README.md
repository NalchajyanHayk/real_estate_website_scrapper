# Spyur Real-Estate Developer Scraper

A deterministic, maintainable Python scraper that collects publicly displayed real-estate developer information from the Russian-language [Spyur business directory](https://www.spyur.am/ru/yellow_pages-1/yp/2639203371/) and exports clean, reviewable CSV datasets.

The project uses ordinary HTTP requests and structured HTML parsing—no browser automation, LLM, paid API, database, authentication, or cloud service is required.

> **Responsible-use notice:** This software is intended for lawful collection of publicly available directory data. Review the website's current terms, robots policy, and applicable laws before running it. The scraper does not bypass authentication, CAPTCHAs, access controls, blocks, or rate limits.

## Table of contents

- [What the project does](#what-the-project-does)
- [Key features](#key-features)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the scraper](#running-the-scraper)
- [Command-line reference](#command-line-reference)
- [Output files](#output-files)
- [Dataset schema](#dataset-schema)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Reliability and data-quality rules](#reliability-and-data-quality-rules)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [Development workflow](#development-workflow)
- [Security and privacy](#security-and-privacy)
- [License](#license)

## What the project does

Starting from the configured Spyur category page, the scraper:

1. Downloads the first category page.
2. Discovers valid numbered category pages.
3. Extracts and validates unique Spyur company-profile URLs.
4. Visits profiles in their original source order, up to the configured limit.
5. Parses available company identity, contact, management, activity, and source metadata.
6. Cleans and conservatively deduplicates values and records.
7. Writes the company dataset and a separate run-summary file as UTF-8 CSV.

The scraper never creates placeholder companies to meet a requested row count. If the source exposes fewer unique profiles than requested, it exports only the profiles that are actually available.

## Key features

- Deterministic parsing with Beautiful Soup and explicit selectors
- Strict validation of category and company-profile URL patterns
- Reusable HTTP session with connection pooling
- Random configurable delay before requests
- Bounded retries for temporary HTTP failures: `429`, `500`, `502`, `503`, and `504`
- Respect for the server's `Retry-After` header
- Per-request connect/read timeouts
- Profile-level fault isolation: one failed company does not stop the remaining run
- Conservative duplicate detection using source URL, name plus phone, and name plus website
- Unicode-safe handling of Russian and Armenian text
- UTF-8 with BOM output for compatibility with spreadsheet applications
- Separate run-summary CSV for traceability
- Offline unit tests using local HTML fixtures and mocked HTTP behavior
- Configurable URL, row limit, timeout, delays, output path, and logging level

## How it works

```text
Spyur category URL
        |
        v
Discover category pages
        |
        v
Extract and validate company links
        |
        v
Fetch each selected profile
        |
        v
Parse -> normalize -> deduplicate
        |
        v
Company CSV + run-summary CSV
```

Parsing is layered so that the most explicit page structures are preferred:

- Company headings and known Spyur profile containers
- Semantic `tel:` and `mailto:` links
- Exact Russian field labels and nearby values
- Address and description containers
- External website and social-network links
- JSON-LD organization data as a secondary fallback

This approach is reproducible and testable. Browser automation would only be appropriate if required information becomes JavaScript-only or the site begins requiring interactive navigation.

## Requirements

- Python **3.11 or newer**
- Internet access for a live scrape
- `pip` for dependency installation

The test suite itself does not require internet access.

### Python dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP sessions, requests, and error handling |
| `beautifulsoup4` | HTML parsing and selector-based extraction |
| `lxml` | Fast parser backend used by Beautiful Soup |
| `pandas` | Tabular CSV generation |
| `pytest` | Automated test suite |

Exact supported version ranges are defined in [`requirements.txt`](requirements.txt).

## Installation

### macOS and Linux

```bash
git clone <your-repository-url>
cd real_estate_website_scrapper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
git clone <your-repository-url>
cd real_estate_website_scrapper
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirm that the correct interpreter is active:

```bash
python --version
```

It must report Python 3.11 or newer.

## Running the scraper

Run with the safe project defaults:

```bash
python main.py
```

Default behavior:

- Source: Spyur's Russian real-estate developer category
- Maximum records: `50`
- Timeout: `20` seconds for both connection and response reading
- Delay before each request: random value from `1.0` to `2.0` seconds
- Log level: `INFO`
- Main output: `output/real_estate_developers.csv`
- Summary output: `output/real_estate_developers_summary.csv`

Example with custom settings:

```bash
python main.py \
  --url "https://www.spyur.am/ru/yellow_pages-1/yp/2639203371/" \
  --output "output/real_estate_developers.csv" \
  --limit 50 \
  --timeout 20 \
  --min-delay 1.0 \
  --max-delay 2.0 \
  --log-level INFO
```

Display built-in help:

```bash
python main.py --help
```

## Command-line reference

| Option | Default | Description |
|---|---:|---|
| `--url URL` | Spyur real-estate category | Starting category URL |
| `--output PATH` | `output/real_estate_developers.csv` | Main CSV destination; the extension must be `.csv` |
| `--limit INTEGER` | `50` | Maximum number of profile links to process; must be greater than zero |
| `--timeout SECONDS` | `20.0` | Connect and read timeout; must be greater than zero |
| `--min-delay SECONDS` | `1.0` | Minimum delay before a request; cannot be negative |
| `--max-delay SECONDS` | `2.0` | Maximum delay before a request; cannot be negative or less than `--min-delay` |
| `--log-level LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

Invalid arguments are rejected before scraping begins. A successful run exits with status `0`; a fatal scrape, filesystem, or output-validation failure exits with status `1`. Argument-parser errors use the standard nonzero `argparse` exit status.

## Output files

Every successful run creates two files in the requested output directory.

### Company dataset

Default path:

```text
output/real_estate_developers.csv
```

Each row represents one successfully parsed, deduplicated company profile. Fields containing multiple values use semicolon-space separators. Missing information remains blank and is never guessed.

### Run summary

Default path:

```text
output/real_estate_developers_summary.csv
```

The filename is derived from the main output name by adding `_summary`. For example, `data/companies.csv` produces `data/companies_summary.csv`.

The summary contains:

- Source category URL
- Scrape timestamp in UTC
- Configured maximum rows
- Available unique profile links
- Successfully exported rows
- Failed profile count
- Removed duplicate count
- A note when the source provides fewer profiles than requested

Both files use UTF-8 with a byte-order mark (`utf-8-sig`) so Cyrillic and Armenian characters display correctly in Excel and similar spreadsheet software.

Generated files under `output/` are intentionally excluded from Git by `.gitignore`.

## Dataset schema

| Column | Type | Description |
|---|---|---|
| `Company Name` | Text | Public company name from the profile heading or structured-data fallback |
| `Legal Name` | Text | Legal/full organization name when explicitly provided |
| `Company Description` | Text | Public profile description or organization type |
| `Director Name` | Text | Listed director or manager name |
| `Director Position` | Text | Listed management role, such as director or general director |
| `Phone Numbers` | Text list | Normalized, deduplicated phone values separated by semicolons |
| `Email Addresses` | Text list | Lowercased, deduplicated email addresses separated by semicolons |
| `Websites` | URL list | External non-social websites separated by semicolons |
| `Addresses` | Text list | Publicly listed addresses separated by semicolons |
| `Activity Types` | Text list | Listed activities, services, or business categories |
| `Social Links` | URL list | Recognized social-network links separated by semicolons |
| `Last Updated` | Text | Source-provided profile update date, when available |
| `Source URL` | URL | Normalized Spyur company-profile URL |
| `Scraped At` | ISO 8601 datetime | UTC time when the profile was parsed |

## Project structure

```text
real_estate_website_scrapper/
├── main.py                         # Command-line entry point
├── pyproject.toml                  # Project metadata and tool configuration
├── requirements.txt                # Runtime and test dependencies
├── scraper/
│   ├── __init__.py
│   ├── category_parser.py          # Category pagination and profile-link extraction
│   ├── cleaner.py                  # Text, phone, email, and URL normalization
│   ├── company_parser.py           # Company-profile field extraction
│   ├── config.py                   # Defaults and runtime configuration model
│   ├── exporter.py                 # Main and summary CSV export
│   ├── http_client.py              # Session, delays, retries, and timeouts
│   ├── models.py                   # Company record and scrape-summary models
│   └── service.py                  # End-to-end orchestration and deduplication
├── tests/
│   ├── fixtures/                   # Reduced local HTML pages used by parser tests
│   ├── test_category_parser.py
│   ├── test_cleaner.py
│   ├── test_company_parser.py
│   ├── test_exporter.py
│   ├── test_http_client.py
│   └── test_service.py
├── output/                         # Generated exports; ignored by Git
├── .gitignore
├── LICENSE
└── README.md
```

## Testing

Install the dependencies and run:

```bash
pytest -v
```

Or use the active interpreter explicitly:

```bash
python -m pytest -v
```

The tests use reduced HTML fixtures and mocked clients, so they do not send requests to Spyur.

### What is tested

| Test module | Responsibility |
|---|---|
| `test_category_parser.py` | Deduplicated company-link extraction, navigation filtering, and pagination discovery |
| `test_cleaner.py` | Whitespace/entity normalization and phone/URL deduplication |
| `test_company_parser.py` | Core profile fields, semantic links, missing optional fields, and flattened list output |
| `test_exporter.py` | Main CSV and sidecar summary creation |
| `test_http_client.py` | Successful response handling and propagation of timeout/HTTP errors |
| `test_service.py` | Continuation and summary accounting after an individual profile failure |

The `tests/` directory is not required merely to execute `python main.py`, but it should remain in the repository. It is the safety net for detecting parser regressions and website-structure changes during maintenance.

Run a lightweight syntax check with:

```bash
python -m compileall -q main.py scraper tests
```

## Reliability and data-quality rules

### Request behavior

- A single `requests.Session` reuses connections.
- The client sends an identifying user-agent and prefers Russian content.
- Each request is delayed by a random value within the configured range.
- Retries are limited and apply only to `GET` requests and temporary failures.
- The server's `Retry-After` response is respected.
- HTTP errors are surfaced rather than silently converted into empty records.

### Parsing behavior

- Only profile URLs matching Spyur's expected language/company path format are accepted.
- Values are extracted only when supported by page content or structured data.
- Whitespace and HTML entities are normalized without transliterating Unicode text.
- Phone formatting is retained for display while punctuation-free keys are used for comparison.
- Email addresses are normalized to lowercase.
- URLs are restricted to valid HTTP or HTTPS addresses.

### Failure behavior

- Failure to access the initial category page is fatal.
- Finding no valid company links is fatal because it may indicate a changed site structure.
- A failed pagination page is logged and skipped when other pages remain usable.
- A failed company profile is logged and recorded in the in-memory summary; processing continues.
- A parsed profile without a company name is rejected.
- If every selected profile fails, no misleading empty dataset is created.

### Deduplication behavior

A record is removed as a duplicate when an earlier record shares at least one conservative identity key:

- Normalized source URL
- Normalized company name plus first phone number
- Normalized company name plus first website

Name-only matches are retained and logged for review because different companies can have similar names.

## Limitations

- The parser depends on the current server-rendered Spyur HTML structure and Russian field labels.
- Website redesigns or renamed fields may require selector and fixture updates.
- The tool does not execute JavaScript.
- It does not solve CAPTCHAs or evade blocking.
- Only recognized HTTP/HTTPS links and supported profile path patterns are accepted.
- Missing or ambiguous source fields remain blank.
- The configured limit is a maximum, not a guaranteed number of rows.
- The output is a snapshot of public source data at scrape time; accuracy ultimately depends on the source.
- The default command produces CSV files only; it does not write a database or Excel workbook.

## Troubleshooting

### `python` or `python3` is not found

Install Python 3.11 or newer, reopen the terminal, and verify:

```bash
python3 --version
```

### The wrong Python version is active

Create the environment with an explicit compatible interpreter, for example:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
```

### `No module named pytest` or another missing package

Activate the virtual environment and install requirements:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### No company profile links are found

Possible causes include:

- Spyur changed its page structure or URL patterns.
- The supplied `--url` is not a compatible category page.
- The response is an error/block page rather than the expected category HTML.

Run with detailed logging:

```bash
python main.py --log-level DEBUG
```

Then compare the current page structure with the selectors in `scraper/category_parser.py` and update the corresponding test fixtures before changing production parsing logic.

### Some profiles fail but a CSV is still produced

This is expected fault-isolation behavior. Check terminal error logs and the `Failed Rows` value in the summary CSV. Successfully parsed profiles remain useful and are exported.

### The exported text looks corrupted in a spreadsheet

The files are already encoded as UTF-8 with BOM. Import the file as UTF-8 if the spreadsheet application does not detect the encoding automatically.

### Permission denied when writing output

Choose a writable destination:

```bash
python main.py --output "./output/companies.csv"
```

### Output path extension error

The active exporter accepts `.csv` only:

```bash
python main.py --output "output/companies.csv"
```

## Development workflow

Before committing a change:

```bash
python -m compileall -q main.py scraper tests
python -m pytest -v
git diff --check
git status --short
```

When changing a parser:

1. Add or update the smallest representative HTML fixture under `tests/fixtures/`.
2. Add a regression test that describes the expected behavior.
3. Update the parser without weakening URL or field validation unnecessarily.
4. Run the complete offline test suite.
5. Perform a small, responsibly delayed live run only when needed.

Generated caches, virtual environments, local secrets, editor metadata, and `output/` exports are excluded through `.gitignore`.

## Security and privacy

- No credentials or API keys are required by the application.
- Do not commit `.env` files or other local secrets; they are ignored by Git.
- The scraper is designed for public company-directory content, not private or authenticated data.
- Review exported contact data before redistributing or using it for outreach.
- Treat source content as untrusted data when integrating the CSV into another system.

## License

This project is distributed under the terms in [`LICENSE`](LICENSE).
