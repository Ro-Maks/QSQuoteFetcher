"""Unit tests for src/questrade/api/quotes.py."""
from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from questrade.api.client import build_client
from questrade.api.quotes import fetch_quotes
from questrade.models.errors import QuestradeApiError, QuoteUnavailableError
from tests.fixtures.quote_fixtures import (
    mock_quote_response_all,
    mock_quote_response_after_hours,
    mock_quote_response_delayed,
    mock_quote_response_halted,
    mock_quote_response_null_price,
)

BASE_URL = "https://mock.api.questrade.com/"
SYMBOL_IDS = [10001, 20001, 30001]


@pytest.fixture()
def client() -> httpx.Client:
    return build_client("mock-token", BASE_URL)


class TestFetchQuotes:
    def test_returns_all_three_quotes(self, httpx_mock: HTTPXMock, client: httpx.Client):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_all())

        # Act
        quotes = fetch_quotes(SYMBOL_IDS, client)

        # Assert
        assert len(quotes) == 3

    def test_all_last_trade_prices_are_not_none(
        self, httpx_mock: HTTPXMock, client: httpx.Client
    ):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_all())

        # Act
        quotes = fetch_quotes(SYMBOL_IDS, client)

        # Assert
        assert all(q.last_trade_price is not None for q in quotes)

    def test_makes_exactly_one_api_call(self, httpx_mock: HTTPXMock, client: httpx.Client):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_all())

        # Act
        fetch_quotes(SYMBOL_IDS, client)

        # Assert — pytest-httpx raises if unexpected extra calls are made
        assert len(httpx_mock.get_requests()) == 1

    def test_batches_all_ids_in_single_url(self, httpx_mock: HTTPXMock, client: httpx.Client):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_all())

        # Act
        fetch_quotes(SYMBOL_IDS, client)

        # Assert
        request_url = str(httpx_mock.get_requests()[0].url)
        assert "10001" in request_url
        assert "20001" in request_url
        assert "30001" in request_url

    def test_after_hours_bid_ask_none_does_not_raise(
        self, httpx_mock: HTTPXMock, client: httpx.Client
    ):
        """API returns None for bid_price/ask_price outside market hours — must not crash."""
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_after_hours())

        # Act — should not raise despite None bid/ask
        quotes = fetch_quotes(SYMBOL_IDS, client)

        # Assert
        assert len(quotes) == 3
        assert all(q.bid_price is None for q in quotes)
        assert all(q.ask_price is None for q in quotes)
        assert all(q.last_trade_price is not None for q in quotes)

    def test_delayed_data_emits_warning_but_does_not_raise(
        self, httpx_mock: HTTPXMock, client: httpx.Client, caplog
    ):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_delayed())

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            quotes = fetch_quotes(SYMBOL_IDS, client)

        # Assert
        assert quotes[0].delay == 15
        assert "delayed" in caplog.text.lower()

    def test_halted_security_emits_warning_but_does_not_raise(
        self, httpx_mock: HTTPXMock, client: httpx.Client, caplog
    ):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_halted())

        # Act
        import logging
        with caplog.at_level(logging.WARNING):
            quotes = fetch_quotes([10001], client)

        # Assert
        assert quotes[0].is_halted is True
        assert "halted" in caplog.text.lower()

    def test_raises_quote_unavailable_error_when_price_is_none(
        self, httpx_mock: HTTPXMock, client: httpx.Client
    ):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", json=mock_quote_response_null_price())

        # Act / Assert
        with pytest.raises(QuoteUnavailableError):
            fetch_quotes([10001], client)

    def test_raises_questrade_api_error_on_http_500(
        self, httpx_mock: HTTPXMock, client: httpx.Client
    ):
        # Arrange
        httpx_mock.add_response(url__contains="markets/quotes", status_code=500)

        # Act / Assert
        with pytest.raises(QuestradeApiError):
            fetch_quotes(SYMBOL_IDS, client)

    def test_raises_value_error_for_empty_symbol_ids(self, client: httpx.Client):
        # Act / Assert
        with pytest.raises(ValueError, match="at least one symbol ID"):
            fetch_quotes([], client)
