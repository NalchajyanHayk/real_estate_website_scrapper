"""Deterministic parsing of public Spyur company profiles."""

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

from .cleaner import (normalize_email, normalize_url, normalize_whitespace,
                      unique_emails, unique_phones, unique_preserving_order, unique_urls)
from .models import CompanyRecord

FIELD_LABELS = {
    "director": ["Директор", "Руководитель", "Генеральный директор", "Исполнительный директор"],
    "phone": ["Телефон", "Телефоны", "Мобильный"],
    "website": ["Сайт", "Веб-сайт", "Интернет-сайт"],
    "email": ["Эл. почта", "Электронная почта", "E-mail", "Email"],
    "address": ["Адрес", "Юридический адрес", "Фактический адрес"],
    "activity": ["Виды деятельности", "Деятельность", "Услуги"],
    "last_updated": ["Дата обновления", "Информация обновлена", "Последнее обновление"],
}
HEADING_SELECTORS = ("h1.company_name", ".company_header h1", "h1", ".company_name")
SOCIAL_HOSTS = {"facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com", "youtube.com", "t.me", "vk.com"}
APP_HOSTS = {"apps.apple.com", "play.google.com"}
INTERNAL_HOSTS = {"spyur.am", "www.spyur.am"}


def _norm_label(value: str) -> str:
    return (normalize_whitespace(value) or "").rstrip(":").casefold()


def _logical_value(label: Tag) -> Tag | None:
    if label.name == "dt":
        return label.find_next_sibling("dd")
    if label.name in {"th", "td"}:
        return label.find_next_sibling("td")
    sibling = label.find_next_sibling()
    if isinstance(sibling, Tag):
        return sibling
    parent = label.parent
    if isinstance(parent, Tag):
        children = [child for child in parent.children if isinstance(child, Tag)]
        if len(children) >= 2 and label in children:
            index = children.index(label)
            return children[index + 1] if index + 1 < len(children) else None
    return None


def find_value_elements_by_labels(soup: BeautifulSoup, labels: list[str]) -> list[Tag]:
    """Find nearby value containers using exact labels before conservative fuzzy matches."""
    exact = {_norm_label(label) for label in labels}
    candidates = soup.find_all(["dt", "th", "td", "span", "div", "strong", "b", "label"])
    matches = [tag for tag in candidates if _norm_label(tag.get_text(" ", strip=True)) in exact]
    if not matches:
        matches = [tag for tag in candidates if any(
            _norm_label(tag.get_text(" ", strip=True)).startswith(label + ":") for label in exact
        )]
    return [value for tag in matches if (value := _logical_value(tag)) is not None]


def find_value_by_labels(soup: BeautifulSoup, labels: list[str]) -> list[str]:
    """Return normalized text from the nearest logical field-value elements."""
    return unique_preserving_order(
        value.get_text(" ", strip=True) for value in find_value_elements_by_labels(soup, labels)
    )


def _json_ld(soup: BeautifulSoup) -> list[dict]:
    objects: list[dict] = []
    for script in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(script.string or "")
            values = data if isinstance(data, list) else [data]
            objects.extend(value for value in values if isinstance(value, dict))
        except (json.JSONDecodeError, TypeError):
            continue
    return objects


def _external_links(soup: BeautifulSoup, source_url: str) -> tuple[list[str], list[str]]:
    websites: list[str] = []
    social: list[str] = []
    root = soup.select_one(".result_main") or soup
    for anchor in root.select("a[href^='http://'], a[href^='https://']"):
        url = normalize_url(anchor.get("href", ""), source_url)
        host = (urlsplit(url).hostname or "").lower()
        root_host = host.removeprefix("www.")
        if not url or root_host in INTERNAL_HOSTS or root_host in APP_HOSTS:
            continue
        if root_host in SOCIAL_HOSTS or any(root_host.endswith("." + item) for item in SOCIAL_HOSTS):
            social.append(url)
        else:
            websites.append(url)
    return unique_urls(websites), unique_urls(social)


def parse_company_page(html: str, source_url: str) -> CompanyRecord:
    """Parse a profile using semantic links, labels, headings, and JSON-LD fallback."""
    soup = BeautifulSoup(html, "lxml")
    heading = next((soup.select_one(selector) for selector in HEADING_SELECTORS if soup.select_one(selector)), None)
    company_name = normalize_whitespace(heading.get_text(" ", strip=True)) if heading else None
    structured = _json_ld(soup)
    organization = next((obj for obj in structured if str(obj.get("@type", "")).lower() in {"organization", "localbusiness", "corporation"}), {})
    company_name = company_name or normalize_whitespace(str(organization.get("name", "")))

    profile_root = soup.select_one(".result_main") or soup
    phones = unique_phones(a.get("href", "") for a in profile_root.select("a[href^='tel:']"))
    emails = unique_emails(a.get("href", "") for a in profile_root.select("a[href^='mailto:']"))
    websites, social = _external_links(soup, source_url)
    addresses = unique_preserving_order(
        element.get_text(" ", strip=True) for element in profile_root.select(".address_block")
    ) or find_value_by_labels(soup, FIELD_LABELS["address"])
    activities = find_value_by_labels(soup, FIELD_LABELS["activity"])
    updated = next(iter(find_value_by_labels(soup, FIELD_LABELS["last_updated"])), None)
    if not updated:
        for label in profile_root.select(".inner_subtitle"):
            if _norm_label(label.get_text(" ", strip=True)) in {
                _norm_label("Дата обновления информации"), *map(_norm_label, FIELD_LABELS["last_updated"])
            }:
                sibling = label.find_next_sibling()
                updated = normalize_whitespace(sibling.get_text(" ", strip=True)) if sibling else None
                break

    director_values = find_value_by_labels(soup, FIELD_LABELS["director"])
    director_name = director_values[0] if director_values else None
    director_position = None
    for label in FIELD_LABELS["director"]:
        if _norm_label(label) in {_norm_label(t.get_text(" ", strip=True)) for t in soup.find_all(["dt", "th", "span", "div", "strong", "b", "label"])}:
            director_position = label
            break

    if director_name and "," in director_name:
        possible_name, possible_position = director_name.rsplit(",", 1)
        if possible_position.strip().casefold() in {
            "директор", "руководитель", "генеральный директор", "исполнительный директор"
        }:
            director_name = normalize_whitespace(possible_name)
            director_position = normalize_whitespace(possible_position)

    legal = next(iter(find_value_by_labels(soup, ["Юридическое название", "Юридическое наименование", "Полное наименование"])), None)
    description_element = profile_root.select_one(".preview_info_block")
    description = (
        normalize_whitespace(description_element.get_text(" ", strip=True))
        if description_element else
        next(iter(find_value_by_labels(soup, ["Описание", "Тип организации", "О компании"])), None)
    )
    if not phones and organization.get("telephone"):
        phones = unique_phones([str(organization["telephone"])])
    if not emails and organization.get("email"):
        emails = [normalize_email(str(organization["email"]))]
    if not addresses and organization.get("address"):
        address = organization["address"]
        addresses = [normalize_whitespace(str(address.get("streetAddress", ""))) or ""] if isinstance(address, dict) else [str(address)]

    return CompanyRecord(
        company_name=company_name, legal_name=legal, company_description=description,
        director_name=director_name, director_position=director_position,
        phone_numbers=phones, email_addresses=emails, websites=websites,
        addresses=unique_preserving_order(addresses), activity_types=activities,
        social_links=social, last_updated=updated,
        source_url=normalize_url(source_url),
        scraped_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
