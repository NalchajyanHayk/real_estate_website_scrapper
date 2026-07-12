"""Deterministic parsing of Spyur category result pages."""

import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .cleaner import normalize_url, unique_preserving_order

RESULT_LINK_SELECTORS = (
    "#results_list_wrapper a[href*='/companies/']",
    ".results_list a[href*='/companies/']",
    "a[data-counter][href*='/companies/']",
)
PAGINATION_SELECTORS = (".paging a[href]", "a.next_page[href]")
COMPANY_PATH_RE = re.compile(r"^/(?:ru|am|en)/companies/[a-z0-9-]+/\d+/?$", re.I)
CATEGORY_PATH_RE = re.compile(r"^/(?:ru|am|en)/yellow_pages-(\d+)/yp/\d+/?$", re.I)


def _is_company_url(url: str) -> bool:
    return bool(COMPANY_PATH_RE.fullmatch(urlsplit(url).path))


def extract_company_links(html: str, base_url: str) -> list[str]:
    """Extract validated profile URLs from result cards with a narrow fallback."""
    soup = BeautifulSoup(html, "lxml")
    anchors = []
    for selector in RESULT_LINK_SELECTORS:
        anchors.extend(soup.select(selector))
    if not anchors:
        anchors = soup.select("main a[href*='/companies/'], #content a[href*='/companies/']")
    urls = [normalize_url(anchor.get("href", ""), base_url) for anchor in anchors]
    return unique_preserving_order(url for url in urls if _is_company_url(url))


def extract_pagination_links(html: str, base_url: str) -> list[str]:
    """Extract all numbered category-page URLs, preserving page order."""
    soup = BeautifulSoup(html, "lxml")
    anchors = [a for selector in PAGINATION_SELECTORS for a in soup.select(selector)]
    urls = [normalize_url(anchor.get("href", ""), base_url) for anchor in anchors]
    valid = [url for url in urls if CATEGORY_PATH_RE.fullmatch(urlsplit(url).path)]
    return unique_preserving_order(valid)


def extract_result_count(html: str) -> int | None:
    """Extract a labelled result count when the page exposes one."""
    soup = BeautifulSoup(html, "lxml")
    for selector in (".results_count", ".result_count", "[data-result-count]"):
        element = soup.select_one(selector)
        if element:
            raw = element.get("data-result-count") or element.get_text(" ", strip=True)
            match = re.search(r"\d+", raw)
            if match:
                return int(match.group())
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(?:Найдено|Организаци[йя]|Результат(?:ов|ы)?)\D{0,20}(\d+)", text, re.I)
    return int(match.group(1)) if match else None
