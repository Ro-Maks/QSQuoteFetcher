"""Unit tests for src/questrade/api/symbols.py."""
from __future__ import annotations

import httpx
import pytest
from pytest_httpx import HTTPXMock

from questrade.api.client import build_client
from questrade.api.symbols import resolve_symbol_id, resolve_all_symbol_ids
from questrade.models.errors import SymbolNotFoundError
from questrade.models.symbol import SymbolConfig
from tests.fixtures.quote_fixtures import (
    MOCK_SYMBOL_FIE,
    MOCK_SYMBOL_MSFT,
    MOCK_SYMBOL_XEQT,
)

BASE_URL = "https://mock.api.questrade.com/"


@pytest.fixture()
def client() -> httpx.Client:
    return build_client("mock-token", BASE_URL)


class TestResolveSymbolId:
    def test_resolves_msft_on_nasdaq(self, httpx_mock: HTTPXMock, client: httpx.Client):
        # Arrange
        httpx_mock.add_response(url__contains="symbols/search", json=MOCK_SYMBOL_MSFT)

        # Act
        result = resolve_symbol_id("MSFT", "NASDAQ", client)

        # Assert
        assert result == 10001

    def test_resolves_fie_to_on_tsx(self, httpx_mock: HTTPXMock, client: httpx.Client):
        """FIE.TO is the correct Questrade symbol — includes the .TO exchange suffix."""
        # Arrange
        httpx_mock.add_response(url__contains="symbols/search", json=MOCK_SYMBOL_FIE)

        # Act
        result = resolve_symbol_id("FIE.TO", "TSX", client)

        # Assert
        assert result == 20001

    def test_resolves_xeqt_to_on_tsx(self, httpx_mock: HTTPXMock, client: httpx.Client):
        """XEQT.TO is the correct Questrade symbol — includes the .TO exchange suffix."""
        # Arrange
        httpx_mock.add_response(url__contains="symbols/search", json=MOCK_SYMBOL_XEQT)

        # Act
        result = resolve_symbol_id("XEQT.TO", "TSX", client)

        # Assert
        assert result == 30001

    def test_raises_for_unknown_symbol(self, httpx_mock: HTTPXMock, client: httpx.Client):
        # Arrange
        httpx_mock.add_response(url__contains="symbols/search", json={"symbols": []})

        # Act / Assert
        with pytest.raises(SymbolNotFoundError):
            resolve_symbol_id("FAKE", "TSX", client)

    def test_does_not_match_fie_on_wrong_exchange(
        self, httpx_mock: HTTPXMock, client: httpx.Client
    ):
        # Arrange — response returns FIE.TO on TSX, but we ask for NASDAQ
        httpx_mock.add_response(url__contains="symbols/search", json=MOCK_SYMBOL_FIE)

        # Act / Assert
        with pytest.raises(SymbolNotFoundError):
            resolve_symbol_id("FIE.TO", "NASDAQ", client)

    def test_fie_without_suffix_does_not_match(
        self, httpx_mock: HTTPXMock, client: httpx.Client
    ):
        """Searching for plain 'FIE' should not match the 'FIE.TO' API symbol."""
        # Arrange — API returns FIE.TO
        httpx_mock.add_response(url__contains="symbols/search", json=MOCK_SYMBOL_FIE)

        # Act / Assert — FIE (no .TO) must NOT match FIE.TO
        with pytest.raises(SymbolNotFoundError):
            resolve_symbol_id("FIE", "TSX", client)


class TestResolveAllSymbolIds:
    def test_resolves_all_three_targets(self, httpx_mock: HTTPXMock, client: httpx.Client):
        # Arrange — each call returns the correct fixture by matching prefix param
        def _handler(request: httpx.Request) -> httpx.Response:
            prefix = request.url.params.get("prefix", "")
            mapping = {
                "MSFT":    MOCK_SYMBOL_MSFT,
                "FIE.TO":  MOCK_SYMBOL_FIE,
                "XEQT.TO": MOCK_SYMBOL_XEQT,
            }
            return httpx.Response(200, json=mapping.get(prefix, {"symbols": []}))

        httpx_mock.add_callback(_handler, url__contains="symbols/search")

        targets = [
            SymbolConfig("MSFT",    "NASDAQ", "Microsoft"),
            SymbolConfig("FIE.TO",  "TSX",    "iShares FIE"),
            SymbolConfig("XEQT.TO", "TSX",    "iShares XEQT"),
        ]

        # Act
        ids = resolve_all_symbol_ids(targets, client)

        # Assert
        assert ids == [10001, 20001, 30001]
