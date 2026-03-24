"""Pydantic models for Questrade Level 1 quote responses."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Quote(BaseModel):
    """A single Level 1 market quote from Questrade.

    Fields use camelCase aliases to match the Questrade API response.
    Access them via snake_case in Python code.

    Note: bid_price, ask_price, last_trade_price can all be None when
    the market is closed or no trades have been recorded for the session.
    """

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    symbol_id: int                  = Field(alias="symbolId")
    last_trade_price: float | None  = Field(alias="lastTradePrice")
    last_trade_time: str            = Field(alias="lastTradeTime")
    bid_price: float | None         = Field(alias="bidPrice")     # None outside market hours
    ask_price: float | None         = Field(alias="askPrice")     # None outside market hours
    volume: int
    open_price: float | None        = Field(alias="openPrice", default=None)
    high_price: float | None        = Field(alias="highPrice", default=None)
    low_price: float | None         = Field(alias="lowPrice", default=None)
    vwap: float | None              = Field(alias="VWAP", default=None)
    bid_size: int | None            = Field(alias="bidSize", default=None)
    ask_size: int | None            = Field(alias="askSize", default=None)
    last_trade_size: int | None     = Field(alias="lastTradeSize", default=None)
    delay: int
    is_halted: bool                 = Field(alias="isHalted")


class QuoteResponse(BaseModel):
    """Wrapper for the /v1/markets/quotes response array."""

    quotes: list[Quote]
