"""Domain models."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompanyRecord:
    """Structured values parsed from one public company profile."""

    company_name: str | None = None
    legal_name: str | None = None
    company_description: str | None = None
    director_name: str | None = None
    director_position: str | None = None
    phone_numbers: list[str] = field(default_factory=list)
    email_addresses: list[str] = field(default_factory=list)
    websites: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    activity_types: list[str] = field(default_factory=list)
    social_links: list[str] = field(default_factory=list)
    last_updated: str | None = None
    source_url: str | None = None
    scraped_at: str | None = None

    def to_flat_dict(self) -> dict[str, str | None]:
        """Convert lists to semicolon-separated, tabular cells."""
        return {
            "Company Name": self.company_name,
            "Legal Name": self.legal_name,
            "Company Description": self.company_description,
            "Director Name": self.director_name,
            "Director Position": self.director_position,
            "Phone Numbers": "; ".join(self.phone_numbers) or None,
            "Email Addresses": "; ".join(self.email_addresses) or None,
            "Websites": "; ".join(self.websites) or None,
            "Addresses": "; ".join(self.addresses) or None,
            "Activity Types": "; ".join(self.activity_types) or None,
            "Social Links": "; ".join(self.social_links) or None,
            "Last Updated": self.last_updated,
            "Source URL": self.source_url,
            "Scraped At": self.scraped_at,
        }


@dataclass
class ScrapeSummary:
    """Observable totals from a scrape run."""

    category_pages_discovered: int = 0
    company_links_found: int = 0
    profiles_attempted: int = 0
    profiles_successfully_parsed: int = 0
    profiles_failed: int = 0
    duplicates_removed: int = 0
    final_rows_exported: int = 0
    output_path: Path | None = None
    failures: list[tuple[str, str]] = field(default_factory=list)
