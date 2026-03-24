"""Unit tests for src/questrade/api/auth.py."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from pytest_httpx import HTTPXMock

from questrade.api.auth import refresh_token
from questrade.models.errors import TokenRefreshError
from tests.fixtures.quote_fixtures import mock_token_response

TOKEN_URL = "https://login.questrade.com/oauth2/token"


@pytest.fixture(autouse=True)
def _no_persist(monkeypatch):
    """Prevent tests from writing to .env."""
    monkeypatch.setattr("questrade.api.auth.persist_tokens", lambda tokens: None)


class TestRefreshToken:
    def test_returns_valid_auth_tokens_on_success(self, httpx_mock: HTTPXMock):
        # Arrange
        httpx_mock.add_response(url=TOKEN_URL, json=mock_token_response())

        # Act
        tokens = refresh_token("old-refresh-token")

        # Assert
        assert tokens.access_token == "mock-access-token-abc123"
        assert tokens.refresh_token == "mock-refresh-token-xyz789"
        assert tokens.expires_in == 1800

    def test_api_server_always_has_trailing_slash(self, httpx_mock: HTTPXMock):
        # Arrange
        data = {**mock_token_response(), "api_server": "https://api01.iq.questrade.com"}
        httpx_mock.add_response(url=TOKEN_URL, json=data)

        # Act
        tokens = refresh_token("old-refresh-token")

        # Assert
        assert tokens.api_server.endswith("/")

    def test_expires_at_is_approximately_now_plus_expires_in(self, httpx_mock: HTTPXMock):
        # Arrange
        httpx_mock.add_response(url=TOKEN_URL, json=mock_token_response())
        import time
        before = time.time()

        # Act
        tokens = refresh_token("old-refresh-token")
        after = time.time()

        # Assert
        expires_ts = tokens.expires_at.timestamp()
        assert before + 1800 <= expires_ts <= after + 1800

    def test_raises_token_refresh_error_on_http_401(self, httpx_mock: HTTPXMock):
        # Arrange
        httpx_mock.add_response(url=TOKEN_URL, status_code=401)

        # Act / Assert
        with pytest.raises(TokenRefreshError):
            refresh_token("bad-token")

    def test_raises_token_refresh_error_on_http_500(self, httpx_mock: HTTPXMock):
        # Arrange
        httpx_mock.add_response(url=TOKEN_URL, status_code=500)

        # Act / Assert
        with pytest.raises(TokenRefreshError):
            refresh_token("any-token")

    def test_raises_token_refresh_error_on_network_failure(self, httpx_mock: HTTPXMock):
        # Arrange
        httpx_mock.add_exception(httpx.ConnectError("connection refused"))

        # Act / Assert
        with pytest.raises(TokenRefreshError):
            refresh_token("any-token")

    def test_refresh_token_field_differs_from_input(self, httpx_mock: HTTPXMock):
        # Arrange
        httpx_mock.add_response(url=TOKEN_URL, json=mock_token_response())

        # Act
        tokens = refresh_token("old-refresh-token")

        # Assert — new token is the one from the response, not the input
        assert tokens.refresh_token == "mock-refresh-token-xyz789"
        assert tokens.refresh_token != "old-refresh-token"
