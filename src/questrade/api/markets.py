"""Fetch market information from the Questrade API."""
from __future__ import annotations

import logging

import httpx

from questrade.api.client import safe_get
from questrade.models.market import Market, MarketsResponse

logger = logging.getLogger(__name__)


def fetch_markets(client: httpx.Client) -> list[Market]:
    """Fetch available markets and their trading hours.

    Returns:
        List of Market objects with trading venue info and hours.
    """
    response = safe_get(client, "v1/markets")
    data = MarketsResponse.model_validate(response.json())
    logger.debug("Fetched %d markets", len(data.markets))
    return data.markets
