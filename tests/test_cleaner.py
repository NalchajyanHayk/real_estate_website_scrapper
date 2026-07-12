from scraper.cleaner import normalize_whitespace, unique_phones, unique_urls


def test_normalizes_whitespace_and_entities():
    assert normalize_whitespace("  Москва&nbsp;  офис\n 1 ") == "Москва офис 1"


def test_removes_duplicate_phones():
    assert unique_phones(["+374 10 12-34-56", "+374(10)12 34 56"]) == ["+374 10 12-34-56"]


def test_removes_duplicate_urls_and_fragments():
    assert unique_urls(["HTTPS://Example.COM/a#x", "https://example.com/a"]) == ["https://example.com/a"]
