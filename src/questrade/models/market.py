"""Data models for Questrade market information responses."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MarketTradingHours(BaseModel):
    """Trading hours for a market session."""

    model_config = ConfigDict(populate_by_name=True)

    start: str
    end: str


class Market(BaseModel):
    """A single market from the /v1/markets endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    trading_venues: list[str] = Field(alias="tradingVenues", default_factory=list)
    default_trading_venue: str = Field(alias="defaultTradingVenue", default="")
    primary_order_routes: list[str] = Field(
        alias="primaryOrderRoutes", default_factory=list,
    )
    secondary_order_routes: list[str] = Field(
        alias="secondaryOrderRoutes", default_factory=list,
    )
    level1_feeds: list[str] = Field(alias="level1Feeds", default_factory=list)
    extended_start_time: str = Field(alias="extendedStartTime", default="")
    start_time: str = Field(alias="startTime", default="")
    end_time: str = Field(alias="endTime", default="")
    extended_end_time: str = Field(alias="extendedEndTime", default="")
    currency: str = Field(default="USD")
    snap_quotes_limit: int = Field(alias="snapQuotesLimit", default=0)


class MarketsResponse(BaseModel):
    """Wrapper for the /v1/markets response."""

    markets: list[Market]
