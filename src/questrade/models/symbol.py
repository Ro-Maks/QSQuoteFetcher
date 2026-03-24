"""Data models for Questrade symbol search responses."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class SymbolConfig:
    """Configuration for a target security symbol."""

    symbol: str
    exchange: str
    name: str


class SymbolSearchResult(BaseModel):
    """A single result from the /v1/symbols/search endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    symbol_id: int          = Field(alias="symbolId")
    listing_exchange: str   = Field(alias="listingExchange")
    description: str


class SymbolSearchResponse(BaseModel):
    """Wrapper for the /v1/symbols/search response array."""

    symbols: list[SymbolSearchResult]
