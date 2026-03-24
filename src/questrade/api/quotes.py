"""Batched Questrade Level 1 quote fetcher.

Always makes a single API call for all symbol IDs — never one per symbol.
See .github/instructions/api.instructions.md for module rules.
"""
from __future__ import annotations

import logging

import httpx

from questrade.api.client import safe_get
from questrade.models.errors import QuoteUnavailableError
from questrade.models.quote import Quote, QuoteResponse

logger = logging.getLogger(__name__)


def fetch_quotes(symbol_ids: list[int], client: httpx.Client) -> list[Quote]:
    """Fetch Level 1 quotes for the given symbol IDs in a single batched call.

    Args:
        symbol_ids: List of Questrade integer symbol IDs.
        client: Configured httpx.Client (auth + base_url already set).

    Returns:
        List of validated Quote objects in the same order as symbol_ids.

    Raises:
        ValueError: If symbol_ids is empty.
        QuoteUnavailableError: If last_trade_price is None for any symbol.
        QuestradeApiError: On any HTTP error from the API.
    """
    if not symbol_ids:
        raise ValueError("fetch_quotes requires at least one symbol ID.")

    ids_param = ",".join(str(sid) for sid in symbol_ids)
    url = f"v1/markets/quotes?ids={ids_param}"

    response = safe_get(client, url)
    data = QuoteResponse.model_validate(response.json())

    if len(data.quotes) != len(symbol_ids):
        logger.warning(
            "Requested %d quotes but received %d.",
            len(symbol_ids),
            len(data.quotes),
        )

    _validate_quotes(data.quotes)
    return data.quotes


def _validate_quotes(quotes: list[Quote]) -> None:
    """Validate quotes and surface warnings for delayed or halted securities.

    Args:
        quotes: List of Quote objects from the API response.

    Raises:
        QuoteUnavailableError: If last_trade_price is None for any quote.
    """
    for quote in quotes:
        if quote.last_trade_price is None:
            raise QuoteUnavailableError(quote.symbol)

        if quote.delay > 0:
            logger.warning(
                "⚠️  %s: market data is delayed by %d minute(s). "
                "A real-time Level 1 subscription is required for live quotes.",
                quote.symbol,
                quote.delay,
            )

        if quote.is_halted:
            logger.warning("🔴 %s: trading is currently halted.", quote.symbol)
