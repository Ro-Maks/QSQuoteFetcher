"""Symbol → symbolId resolution with in-process caching.

See .github/instructions/api.instructions.md for module rules.
"""
from __future__ import annotations

import logging

import httpx

from questrade.api.client import safe_get
from questrade.models.errors import SymbolNotFoundError
from questrade.models.symbol import SymbolConfig, SymbolSearchResponse, SymbolSearchResult

logger = logging.getLogger(__name__)

# In-process cache: "SYMBOL:EXCHANGE" → symbolId
# Valid for the lifetime of one process execution only.
_symbol_cache: dict[str, int] = {}


def resolve_symbol_id(
    symbol: str,
    exchange: str,
    client: httpx.Client,
) -> int:
    """Resolve a ticker symbol and exchange to its Questrade symbolId.

    Results are cached in memory for the current process — a second call
    with the same symbol + exchange will not make another API request.

    Args:
        symbol: The ticker string, e.g. "MSFT".
        exchange: The listing exchange, e.g. "NASDAQ" or "TSX".
        client: Configured httpx.Client (auth + base_url already set).

    Returns:
        The integer symbolId for use in quote requests.

    Raises:
        SymbolNotFoundError: If no exact symbol + exchange match is found.
        QuestradeApiError: On any HTTP error from the API.
    """
    cache_key = f"{symbol.upper()}:{exchange.upper()}"

    if cache_key in _symbol_cache:
        logger.debug("Symbol cache hit: %s", cache_key)
        return _symbol_cache[cache_key]

    url = f"v1/symbols/search?prefix={symbol}"
    response = safe_get(client, url)
    data = SymbolSearchResponse.model_validate(response.json())

    match = next(
        (
            s for s in data.symbols
            if s.symbol.upper() == symbol.upper()
            and s.listing_exchange.upper() == exchange.upper()
        ),
        None,
    )

    if match is None:
        raise SymbolNotFoundError(symbol, exchange)

    _symbol_cache[cache_key] = match.symbol_id
    logger.debug("Resolved %s → symbolId %d", cache_key, match.symbol_id)
    return match.symbol_id


def search_symbols(
    prefix: str,
    client: httpx.Client,
) -> list[SymbolSearchResult]:
    """Search for symbols by prefix.

    Returns raw search results for display in autocomplete UI.
    """
    url = f"v1/symbols/search?prefix={prefix}"
    response = safe_get(client, url)
    data = SymbolSearchResponse.model_validate(response.json())
    return data.symbols


def resolve_all_symbol_ids(
    targets: list[SymbolConfig],
    client: httpx.Client,
) -> list[int]:
    """Resolve all target symbols to their symbolIds.

    Calls resolve_symbol_id() for each target sequentially.
    Results are cached so repeat calls within a process are free.

    Args:
        targets: List of SymbolConfig objects from config.TARGET_SYMBOLS.
        client: Configured httpx.Client.

    Returns:
        List of symbolIds in the same order as the input targets.

    Raises:
        SymbolNotFoundError: If any symbol fails to resolve.
    """
    ids: list[int] = []
    for target in targets:
        symbol_id = resolve_symbol_id(target.symbol, target.exchange, client)
        ids.append(symbol_id)
    return ids
