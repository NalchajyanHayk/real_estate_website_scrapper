"""End-to-end scraping orchestration."""

import logging
import re
from urllib.parse import urlsplit

from .category_parser import extract_company_links, extract_pagination_links
from .cleaner import normalize_url, phone_comparison_key, unique_preserving_order
from .company_parser import parse_company_page
from .config import ScraperConfig
from .http_client import HttpClient
from .models import CompanyRecord, ScrapeSummary

LOGGER = logging.getLogger(__name__)


class ScrapeError(RuntimeError):
    """A fatal error that prevents a meaningful output."""


def _name_key(value: str | None) -> str:
    return re.sub(r"[^\w]+", "", (value or "").casefold())


class SpyurScraper:
    """Discover category pages and parse profiles without fabricating data."""

    def __init__(self, config: ScraperConfig, client: HttpClient) -> None:
        self.config = config
        self.client = client

    def _discover_category_pages(self, first_html: str) -> list[str]:
        discovered = extract_pagination_links(first_html, self.config.base_url)
        return discovered or [normalize_url(self.config.start_url)]

    def _deduplicate_records(self, records: list[CompanyRecord]) -> tuple[list[CompanyRecord], int]:
        kept: list[CompanyRecord] = []
        exact: set[tuple[str, ...]] = set()
        names: dict[str, CompanyRecord] = {}
        removed = 0
        for record in records:
            name = _name_key(record.company_name)
            keys: list[tuple[str, ...]] = []
            if record.source_url:
                keys.append(("url", normalize_url(record.source_url)))
            if name and record.phone_numbers:
                keys.append(("phone", name, phone_comparison_key(record.phone_numbers[0])))
            if name and record.websites:
                keys.append(("website", name, normalize_url(record.websites[0])))
            if any(key in exact for key in keys):
                removed += 1
                LOGGER.warning("Duplicate record removed: %s", record.company_name)
                continue
            if not keys and name in names:
                LOGGER.warning("Potential name-only duplicate retained for review: %s", record.company_name)
            exact.update(keys)
            if name:
                names[name] = record
            kept.append(record)
        return kept, removed

    def run(self) -> tuple[list[CompanyRecord], ScrapeSummary]:
        """Run discovery and parsing; continue after individual profile failures."""
        summary = ScrapeSummary(output_path=self.config.output_path)
        LOGGER.info("Starting category URL: %s", self.config.start_url)
        try:
            first_html = self.client.get_html(self.config.start_url)
        except Exception as exc:
            raise ScrapeError(f"Category page is inaccessible: {exc}") from exc
        pages = self._discover_category_pages(first_html)
        summary.category_pages_discovered = len(pages)
        LOGGER.info("Category pages discovered: %d", len(pages))
        # The numbered page-1 link may differ from start_url only by a slash/query.
        # It represents the HTML already fetched and must not be requested twice.
        html_by_url = {pages[0]: first_html}
        links: list[str] = []
        for page_url in pages:
            try:
                html = html_by_url.get(page_url) or self.client.get_html(page_url)
            except Exception as exc:
                LOGGER.error("Category pagination page failed: %s: %s", page_url, exc)
                continue
            links.extend(extract_company_links(html, self.config.base_url))
        links = unique_preserving_order(links)
        summary.company_links_found = len(links)
        LOGGER.info("Unique company links discovered: %d", len(links))
        if not links:
            raise ScrapeError("No company profile links found; the page structure may have changed")
        if len(links) < self.config.max_rows:
            LOGGER.warning("Website offers %d unique profiles, fewer than requested limit %d; no rows will be fabricated", len(links), self.config.max_rows)
        selected = links[: self.config.max_rows]
        records: list[CompanyRecord] = []
        for index, url in enumerate(selected, 1):
            summary.profiles_attempted += 1
            LOGGER.info("Scraping company %d/%d: %s", index, len(selected), url)
            try:
                record = parse_company_page(self.client.get_html(url), url)
                if not record.company_name:
                    raise ValueError("profile has no company heading")
                records.append(record)
                summary.profiles_successfully_parsed += 1
                if not record.director_name:
                    LOGGER.warning("Missing director for: %s", record.company_name)
            except Exception as exc:
                summary.profiles_failed += 1
                summary.failures.append((url, str(exc)))
                LOGGER.error("Failed profile %s: %s", url, exc)
        records, removed = self._deduplicate_records(records)
        summary.duplicates_removed = removed
        summary.final_rows_exported = len(records)
        if not records:
            raise ScrapeError("All profile pages failed; no meaningful workbook can be created")
        return records, summary
