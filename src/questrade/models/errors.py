"""Custom exception hierarchy for all Questrade API failures.

See .github/prompts/error-handling.prompt.md for full usage patterns.
"""
from __future__ import annotations


class QuestradeApiError(Exception):
    """Base exception for all Questrade API failures."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.cause = cause


class SymbolNotFoundError(QuestradeApiError):
    """Raised when symbol + exchange lookup returns no match."""

    def __init__(self, symbol: str, exchange: str) -> None:
        super().__init__(f"Symbol '{symbol}' not found on exchange '{exchange}'")


class QuoteUnavailableError(QuestradeApiError):
    """Raised when last_trade_price is None (no trades recorded)."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"No trade price available for '{symbol}'")


class TokenRefreshError(QuestradeApiError):
    """Raised when the OAuth token refresh call fails."""


class RateLimitError(QuestradeApiError):
    """Raised when Questrade returns HTTP 429."""

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after_seconds or '?'}s",
            status_code=429,
        )
        self.retry_after_seconds = retry_after_seconds
