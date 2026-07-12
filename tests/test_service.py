from pathlib import Path

from scraper.config import ScraperConfig
from scraper.service import SpyurScraper


class FakeClient:
    def __init__(self, pages):
        self.pages = pages

    def get_html(self, url):
        value = self.pages[url]
        if isinstance(value, Exception):
            raise value
        return value


def test_failed_profile_does_not_abort_run():
    start = "https://www.spyur.am/ru/yellow_pages-1/yp/2639203371/"
    good = "https://www.spyur.am/ru/companies/good/1"
    bad = "https://www.spyur.am/ru/companies/bad/2"
    category = f'<main id="content"><div id="results_list_wrapper"><a data-counter="1" href="{good}">Good</a><a data-counter="2" href="{bad}">Bad</a></div></main>'
    pages = {start: category, good: "<h1>Good Co</h1>", bad: RuntimeError("broken")}
    config = ScraperConfig(start_url=start, max_rows=50, min_delay_seconds=0, max_delay_seconds=0, output_path=Path("x.csv"))
    records, summary = SpyurScraper(config, FakeClient(pages)).run()
    assert [record.company_name for record in records] == ["Good Co"]
    assert summary.profiles_failed == 1
