"""Configuration for the scraper."""

from dataclasses import dataclass, field
from pathlib import Path

BASE_URL = "https://www.spyur.am"
START_URL = "https://www.spyur.am/ru/yellow_pages-1/yp/2639203371/"
OUTPUT_PATH = Path("output/real_estate_developers.csv")
DEFAULT_HEADERS = {
    "User-Agent": "SpyurRealEstateScraper/1.0 (+public-directory research; requests)",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.6",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass(frozen=True)
class ScraperConfig:
    """Runtime settings, overridable by the command line."""

    base_url: str = BASE_URL
    start_url: str = START_URL
    output_path: Path = OUTPUT_PATH
    max_rows: int = 50
    request_timeout: float = 20.0
    min_delay_seconds: float = 1.0
    max_delay_seconds: float = 2.0
    max_retries: int = 3
    backoff_factor: float = 1.0
    headers: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HEADERS))
    preferred_language: str = "ru"
    log_level: str = "INFO"
