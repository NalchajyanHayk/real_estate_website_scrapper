from pathlib import Path

from scraper.company_parser import parse_company_page

HTML = (Path(__file__).parent / "fixtures/company_page.html").read_text()
URL = "https://www.spyur.am/ru/companies/acme-development/101"


def test_extracts_profile_fields_and_semantic_links():
    record = parse_company_page(HTML, URL)
    assert record.company_name == "«ACME» Development"
    assert record.director_name == "Иван Иванов"
    assert record.director_position == "Директор"
    assert record.phone_numbers == ["+374 10 12-34-56", "+374 91 00-00-00"]
    assert record.email_addresses == ["info@acme.am"]
    assert record.websites == ["https://acme.am/", "https://second.acme.am/projects"]
    assert record.social_links == ["https://facebook.com/acme"]
    assert record.addresses == ["Ереван, ул. Абовяна, 1"]


def test_missing_optional_fields_are_blank():
    record = parse_company_page("<html><body><h1>Minimal Co</h1></body></html>", URL)
    assert record.director_name is None
    assert record.websites == []


def test_flat_dictionary_joins_lists():
    flat = parse_company_page(HTML, URL).to_flat_dict()
    assert flat["Phone Numbers"] == "+374 10 12-34-56; +374 91 00-00-00"
    assert "[" not in flat["Websites"]
