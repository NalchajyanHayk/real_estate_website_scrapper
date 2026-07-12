"""CSV data and scrape-summary export."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import ScraperConfig
from .models import CompanyRecord, ScrapeSummary


def export_to_csv(
    records: list[CompanyRecord],
    output_path: Path,
    config: ScraperConfig | None = None,
    summary: ScrapeSummary | None = None,
) -> Path:
    """Write company records to CSV and run metadata to a sidecar summary CSV."""
    if output_path.suffix.lower() != ".csv":
        raise ValueError("output path must use the .csv extension")
    config = config or ScraperConfig(output_path=output_path)
    summary = summary or ScrapeSummary(
        company_links_found=len(records), profiles_successfully_parsed=len(records)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns = list(CompanyRecord().to_flat_dict())
    frame = pd.DataFrame([record.to_flat_dict() for record in records], columns=columns)
    # UTF-8 with BOM makes Russian and Armenian text open correctly in Excel too.
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")

    note = ""
    if summary.company_links_found < config.max_rows:
        note = (
            f"Source offered {summary.company_links_found} unique profile links, fewer than "
            f"configured limit {config.max_rows}; no rows were fabricated."
        )
    summary_rows = [
        ("Source Category URL", config.start_url),
        ("Scrape Timestamp (UTC)", datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
        ("Configured Maximum Rows", config.max_rows),
        ("Available Profile Links", summary.company_links_found),
        ("Successful Rows", len(records)),
        ("Failed Rows", summary.profiles_failed),
        ("Duplicate Count", summary.duplicates_removed),
        ("Note", note),
    ]
    summary_path = output_path.with_name(f"{output_path.stem}_summary.csv")
    pd.DataFrame(summary_rows, columns=["Metric", "Value"]).to_csv(
        summary_path, index=False, encoding="utf-8-sig"
    )
    return output_path
