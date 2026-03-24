"""Shared mock API response data for unit tests.

All test modules should import fixtures from here — never define
inline response dicts in individual test files.

NOTE: FIE.TO and XEQT.TO are the correct Questrade symbol names for
these Canadian ETFs. The API returns the full ticker with exchange suffix.
"""
from __future__ import annotations


def mock_token_response() -> dict:
    return {
        "access_token": "mock-access-token-abc123",
        "refresh_token": "mock-refresh-token-xyz789",
        "api_server": "https://mock.api.questrade.com/",
        "token_type": "Bearer",
        "expires_in": 1800,
    }


def mock_symbol_search(symbol: str, symbol_id: int, exchange: str, name: str) -> dict:
    return {
        "symbols": [
            {
                "symbol": symbol,
                "symbolId": symbol_id,
                "listingExchange": exchange,
                "description": name,
            }
        ]
    }


MOCK_SYMBOL_MSFT   = mock_symbol_search("MSFT",    10001, "NASDAQ", "Microsoft Corporation")
MOCK_SYMBOL_FIE    = mock_symbol_search("FIE.TO",  20001, "TSX",    "iShares Canadian Financial Monthly Income ETF")
MOCK_SYMBOL_XEQT   = mock_symbol_search("XEQT.TO", 30001, "TSX",    "iShares Core Equity ETF Portfolio")


def _mock_quote(
    symbol: str,
    symbol_id: int,
    last_trade_price: float | None = 100.00,
    bid_price: float | None = None,
    ask_price: float | None = None,
    open_price: float | None = 98.50,
    delay: int = 0,
    is_halted: bool = False,
) -> dict:
    """Build a single mock quote dict.

    bid_price and ask_price default to None to match API behaviour
    outside market hours.
    """
    return {
        "symbol": symbol,
        "symbolId": symbol_id,
        "lastTradePrice": last_trade_price,
        "lastTradeTime": "2026-03-21T19:34:12.000000-04:00",
        "bidPrice": bid_price,
        "askPrice": ask_price,
        "openPrice": open_price,
        "volume": 1_500_000,
        "delay": delay,
        "isHalted": is_halted,
    }


def mock_quote_response_all() -> dict:
    """Standard response: all three symbols, real-time, active."""
    return {
        "quotes": [
            _mock_quote("MSFT",    10001, last_trade_price=415.23, bid_price=415.20, ask_price=415.26),
            _mock_quote("FIE.TO",  20001, last_trade_price=8.92,   bid_price=8.91,   ask_price=8.93),
            _mock_quote("XEQT.TO", 30001, last_trade_price=31.47,  bid_price=31.45,  ask_price=31.49),
        ]
    }


def mock_quote_response_after_hours() -> dict:
    """Quotes with None bid/ask (market closed) — this is normal API behaviour."""
    return {
        "quotes": [
            _mock_quote("MSFT",    10001, last_trade_price=415.23, bid_price=None, ask_price=None),
            _mock_quote("FIE.TO",  20001, last_trade_price=8.92,   bid_price=None, ask_price=None),
            _mock_quote("XEQT.TO", 30001, last_trade_price=31.47,  bid_price=None, ask_price=None),
        ]
    }


def mock_quote_response_delayed() -> dict:
    """All three symbols with delay=15."""
    return {
        "quotes": [
            _mock_quote("MSFT",    10001, last_trade_price=415.23, delay=15),
            _mock_quote("FIE.TO",  20001, last_trade_price=8.92,   delay=15),
            _mock_quote("XEQT.TO", 30001, last_trade_price=31.47,  delay=15),
        ]
    }


def mock_quote_response_null_price() -> dict:
    """MSFT with null last_trade_price."""
    return {"quotes": [_mock_quote("MSFT", 10001, last_trade_price=None)]}


def mock_quote_response_halted() -> dict:
    """MSFT with is_halted=True."""
    return {"quotes": [_mock_quote("MSFT", 10001, is_halted=True)]}
