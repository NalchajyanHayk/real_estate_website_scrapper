"""Command-line entry point."""

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from scraper.config import ScraperConfig
from scraper.exporter import export_to_csv
from scraper.http_client import HttpClient
from scraper.service import ScrapeError, SpyurScraper


def positive(value: str) -> float:
    """Argparse type for positive numeric values."""
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description="Export Spyur real-estate developers to CSV")
    parser.add_argument("--url", default=ScraperConfig().start_url)
    parser.add_argument("--output", type=Path, default=ScraperConfig().output_path)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--timeout", type=positive, default=20.0)
    parser.add_argument("--min-delay", type=float, default=1.0)
    parser.add_argument("--max-delay", type=float, default=2.0)
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    return parser


def main() -> int:
    """Validate arguments, run the scrape, and export the workbook."""
    parser = build_parser()
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be greater than zero")
    if args.min_delay < 0 or args.max_delay < 0:
        parser.error("delays cannot be negative")
    if args.min_delay > args.max_delay:
        parser.error("--min-delay cannot exceed --max-delay")
    logging.basicConfig(level=args.log_level, format="[%(levelname)s] %(message)s")
    config = replace(ScraperConfig(), start_url=args.url, output_path=args.output,
                     max_rows=args.limit, request_timeout=args.timeout,
                     min_delay_seconds=args.min_delay, max_delay_seconds=args.max_delay,
                     log_level=args.log_level)
    try:
        records, summary = SpyurScraper(config, HttpClient(config)).run()
        export_to_csv(records, config.output_path, config, summary)
    except (ScrapeError, OSError, ValueError) as exc:
        logging.error("Scrape failed: %s", exc)
        return 1
    logging.info("Exported %d rows to %s (%d profile failures, %d duplicates removed)",
                 len(records), config.output_path, summary.profiles_failed, summary.duplicates_removed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
