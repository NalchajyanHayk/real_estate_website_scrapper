from unittest.mock import Mock

import pytest
import requests

from scraper.config import ScraperConfig
from scraper.http_client import HttpClient


def client_with(response):
    session = Mock()
    session.headers = {}
    session.mount = Mock()
    session.get.return_value = response
    return HttpClient(ScraperConfig(min_delay_seconds=0, max_delay_seconds=0), session=session, sleep=lambda _: None), session


def test_successful_response():
    response = Mock(text="<html>ok</html>", encoding="utf-8")
    response.raise_for_status.return_value = None
    client, _ = client_with(response)
    assert client.get_html("https://example.com") == "<html>ok</html>"


@pytest.mark.parametrize("exception", [requests.Timeout("timeout"), requests.HTTPError("404")])
def test_request_errors_propagate(exception):
    response = Mock(encoding="utf-8")
    response.raise_for_status.side_effect = exception
    client, _ = client_with(response)
    with pytest.raises(requests.RequestException):
        client.get_html("https://example.com")
