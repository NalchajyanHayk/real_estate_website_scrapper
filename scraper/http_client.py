"""Polite reusable HTTP client."""

import logging
import random
import time
from typing import Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import ScraperConfig

LOGGER = logging.getLogger(__name__)


class HttpClient:
    """Fetch HTML with connection reuse, bounded retries, and delays."""

    def __init__(self, config: ScraperConfig, session: requests.Session | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.sleep = sleep
        self.session.headers.update(config.headers)
        retry = Retry(
            total=config.max_retries,
            connect=config.max_retries,
            read=config.max_retries,
            status=config.max_retries,
            backoff_factor=config.backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_html(self, url: str) -> str:
        """Fetch one document, failing clearly on blocks and HTTP errors."""
        delay = random.uniform(self.config.min_delay_seconds, self.config.max_delay_seconds)
        if delay:
            self.sleep(delay)
        LOGGER.debug("Requesting %s", url)
        try:
            response = self.session.get(
                url, timeout=(self.config.request_timeout, self.config.request_timeout)
            )
            response.raise_for_status()
            if not response.encoding or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.RequestException:
            LOGGER.exception("Failed request after retries: %s", url)
            raise
