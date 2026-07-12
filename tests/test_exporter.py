import csv

from scraper.config import ScraperConfig
from scraper.exporter import export_to_csv
from scraper.models import CompanyRecord, ScrapeSummary


def test_exports_csv_and_summary_without_index(tmp_path):
    output = tmp_path / "companies.csv"
    record = CompanyRecord(company_name="Тест", phone_numbers=["+374-10-123456"])
    config = ScraperConfig(output_path=output, max_rows=50)
    summary = ScrapeSummary(company_links_found=1, profiles_successfully_parsed=1)
    export_to_csv([record], output, config, summary)

    with output.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["Company Name"] == "Тест"
    assert rows[0]["Phone Numbers"] == "+374-10-123456"
    assert (tmp_path / "companies_summary.csv").exists()
