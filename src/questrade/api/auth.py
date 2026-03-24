"""Questrade OAuth 2.0 token refresh and rotation.

See .github/prompts/refresh-token.prompt.md for full implementation guidance.
"""
from __future__ import annotations

import logging

import httpx

from questrade.config import get_env, persist_env
from questrade.models.auth import AuthTokens, TokenResponse
from questrade.models.errors import TokenRefreshError

logger = logging.getLogger(__name__)

TOKEN_URL = "https://login.questrade.com/oauth2/token"


def refresh_token(current_refresh_token: str) -> AuthTokens:
    """Refresh the Questrade access token using the current refresh token.

    The refresh token rotates on every successful call. The new token and
    api_server URL are persisted to .env automatically.

    Args:
        current_refresh_token: The current long-lived refresh token.

    Returns:
        Fresh AuthTokens with the new access token, rotated refresh token,
        and updated api_server URL.

    Raises:
        TokenRefreshError: On any HTTP error or network failure.
    """
    try:
        response = httpx.post(
            TOKEN_URL,
            params={
                "grant_type": "refresh_token",
                "refresh_token": current_refresh_token,
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TokenRefreshError(
            f"Token refresh failed with HTTP {exc.response.status_code}",
            status_code=exc.response.status_code,
            cause=exc,
        ) from exc
    except httpx.RequestError as exc:
        raise TokenRefreshError(
            f"Network error during token refresh: {exc}",
            cause=exc,
        ) from exc

    raw = TokenResponse.model_validate(response.json())
    tokens = AuthTokens.from_response(raw)

    persist_tokens(tokens)
    logger.info("Token refreshed successfully. Expires at: %s", tokens.expires_at.isoformat())

    return tokens


def persist_tokens(tokens: AuthTokens) -> None:
    """Persist the rotated refresh token and api_server to .env.

    Called automatically by refresh_token(). No need to call manually.

    Args:
        tokens: The newly issued AuthTokens object.
    """
    persist_env("QUESTRADE_REFRESH_TOKEN", tokens.refresh_token)
    persist_env("QUESTRADE_API_SERVER", tokens.api_server)


def get_initial_tokens() -> AuthTokens:
    """Convenience wrapper: load refresh token from env and refresh.

    Returns:
        Fresh AuthTokens ready for API calls.

    Raises:
        TokenRefreshError: If the token endpoint returns an error.
        EnvironmentError: If QUESTRADE_REFRESH_TOKEN is not set.
    """
    return refresh_token(get_env("QUESTRADE_REFRESH_TOKEN"))
