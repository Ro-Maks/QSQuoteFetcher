"""Fetch historical candlestick data from the Questrade API."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx

from questrade.api.client import safe_get
from questrade.models.candle import Candle, CandlesResponse

logger = logging.getLogger(__name__)


def fetch_candles(
    symbol_id: int,
    start: datetime,
    end: datetime,
    interval: str,
    client: httpx.Client,
) -> list[Candle]:
    """Fetch historical OHLCV candles for a symbol.

    Args:
        symbol_id: Questrade symbol ID.
        start: Start datetime (UTC).
        end: End datetime (UTC).
        interval: Candle interval — e.g. "FiveMinutes", "OneHour", "OneDay".
        client: Configured httpx.Client.

    Returns:
        List of Candle objects.
    """
    start_str = start.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000000-00:00")
    end_str = end.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000000-00:00")
    url = (
        f"v1/markets/candles/{symbol_id}"
        f"?startTime={start_str}"
        f"&endTime={end_str}"
        f"&interval={interval}"
    )
    response = safe_get(client, url)
    data = CandlesResponse.model_validate(response.json())
    logger.debug(
        "Fetched %d candles for symbol %d (%s)", len(data.candles), symbol_id, interval,
    )
    return data.candles
