"""Data models for Questrade historical candle responses."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Candle(BaseModel):
    """A single OHLCV candlestick from /v1/markets/candles/{id}."""

    model_config = ConfigDict(populate_by_name=True)

    start: str
    end: str
    open: float = Field(alias="open")
    high: float
    low: float
    close: float
    volume: int
    vwap: float = Field(alias="VWAP", default=0.0)


class CandlesResponse(BaseModel):
    """Wrapper for the /v1/markets/candles response."""

    candles: list[Candle]
