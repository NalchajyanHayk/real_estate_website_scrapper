from pathlib import Path

from scraper.category_parser import extract_company_links, extract_pagination_links

HTML = (Path(__file__).parent / "fixtures/category_page.html").read_text()


def test_extracts_deduplicated_company_links_and_ignores_navigation():
    links = extract_company_links(HTML, "https://www.spyur.am")
    assert links == ["https://www.spyur.am/ru/companies/acme-development/101", "https://www.spyur.am/ru/companies/beta-build/102"]
    assert not any("footer-company" in link for link in links)


def test_discovers_all_pagination_pages():
    pages = extract_pagination_links(HTML, "https://www.spyur.am")
    assert ["yellow_pages-1", "yellow_pages-2", "yellow_pages-3"] == [page.split("/yp/")[0].rsplit("/", 1)[-1] for page in pages]
