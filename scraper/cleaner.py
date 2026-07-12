"""Value cleaning and URL normalization helpers."""

import html
import re
from collections.abc import Iterable
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit


def normalize_whitespace(value: str | None) -> str | None:
    """Decode entities and collapse whitespace without altering Unicode text."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", html.unescape(value).replace("\xa0", " ")).strip()
    return cleaned or None


def normalize_phone(value: str) -> str:
    """Return a readable phone value while preserving its leading plus."""
    value = unquote(value.removeprefix("tel:")).split("?", 1)[0]
    return normalize_whitespace(value) or ""


def phone_comparison_key(value: str) -> str:
    """Return a conservative phone key without guessing a country code."""
    value = normalize_phone(value)
    prefix = "+" if value.startswith("+") else ""
    return prefix + re.sub(r"[^0-9]", "", value)


def normalize_email(value: str) -> str:
    """Normalize a plain email address or mailto URI."""
    value = unquote(value.strip())
    if value.lower().startswith("mailto:"):
        value = value[7:]
    return value.split("?", 1)[0].strip().lower()


def normalize_url(value: str, base_url: str | None = None) -> str:
    """Resolve and normalize an HTTP(S) URL, retaining meaningful queries."""
    value = value.strip()
    if not value or value.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""
    absolute = urljoin(base_url or "", value)
    try:
        parts = urlsplit(absolute)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return ""
        host = parts.hostname.lower()
        port = f":{parts.port}" if parts.port else ""
        path = re.sub(r"/{2,}", "/", parts.path or "/")
        return urlunsplit((parts.scheme.lower(), host + port, path, parts.query, ""))
    except ValueError:
        return ""


def unique_preserving_order(values: Iterable[str]) -> list[str]:
    """Remove empty and duplicate strings, preserving their first occurrence."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = normalize_whitespace(value)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def unique_phones(values: Iterable[str]) -> list[str]:
    """Deduplicate phones by punctuation-free comparison form."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        display = normalize_phone(value)
        key = phone_comparison_key(display)
        if display and key and key not in seen:
            seen.add(key)
            result.append(display)
    return result


def unique_emails(values: Iterable[str]) -> list[str]:
    """Normalize and deduplicate email values case-insensitively."""
    return unique_preserving_order(normalize_email(value) for value in values)


def unique_urls(values: Iterable[str], base_url: str | None = None) -> list[str]:
    """Normalize and deduplicate URLs."""
    return unique_preserving_order(normalize_url(value, base_url) for value in values)
