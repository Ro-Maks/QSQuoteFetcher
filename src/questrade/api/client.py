"""Shared httpx client with Bearer auth injection and 401 retry logic."""
from __future__ import annotations

import httpx

from questrade.models.errors import (
    QuestradeApiError,
    RateLimitError,
    TokenRefreshError,
)

class BearerAuth(httpx.Auth):
    """httpx Auth class that injects a Bearer token into every request."""

    def __init__(self, token: str) -> None:
        self.token = token

    def auth_flow(
        self, request: httpx.Request
    ):  # type: ignore[override]
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


def build_client(access_token: str, api_server: str) -> httpx.Client:
    """Create a configured httpx.Client for the Questrade API.

    Args:
        access_token: Valid Bearer token for Authorization header.
        api_server: Dynamic Questrade base URL (e.g. https://api01.iq.questrade.com/).

    Returns:
        Configured httpx.Client instance.
    """
    return httpx.Client(
        base_url=api_server,
        auth=BearerAuth(access_token),
        timeout=10.0,
        headers={"Content-Type": "application/json"},
    )


def safe_get(client: httpx.Client, url: str) -> httpx.Response:
    """Execute a GET request and convert HTTP errors to typed exceptions.

    Handles:
    - 401: caller should refresh token and retry (raises TokenRefreshError)
    - 429: raises RateLimitError with retry_after seconds
    - Other 4xx/5xx: raises QuestradeApiError

    Args:
        client: Configured httpx.Client instance.
        url: The relative or absolute URL to GET.

    Returns:
        The successful httpx.Response object.

    Raises:
        TokenRefreshError: On HTTP 401.
        RateLimitError: On HTTP 429.
        QuestradeApiError: On any other HTTP error.
    """
    try:
        response = client.get(url)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code

        if status == 401:
            raise TokenRefreshError(
                "Access token expired or invalid (HTTP 401)",
                status_code=401,
                cause=exc,
            ) from exc

        if status == 429:
            retry_after_raw = exc.response.headers.get("retry-after", "60")
            retry_after = int(retry_after_raw) if retry_after_raw.isdigit() else 60
            raise RateLimitError(retry_after) from exc

        raise QuestradeApiError(
            f"Questrade API error: {exc.response.status_code}",
            status_code=status,
            cause=exc,
        ) from exc

    except httpx.RequestError as exc:
        raise QuestradeApiError(
            f"Network error: {exc}",
            cause=exc,
        ) from exc
