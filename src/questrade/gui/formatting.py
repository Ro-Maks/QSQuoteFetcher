"""Formatting helpers for GUI display."""
from __future__ import annotations

from datetime import datetime

from questrade.models.quote import Quote

_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def fmt_price(value: float | None) -> str:
    """Format a price as '$X,XXX.XX' or '---'."""
    return f"${value:,.2f}" if value is not None else "---"


def fmt_volume(volume: int) -> str:
    """Format volume with K/M suffixes."""
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:,.1f}M"
    if volume >= 1_000:
        return f"{volume / 1_000:,.1f}K"
    return f"{volume:,}"


def fmt_time(iso_str: str) -> str:
    """Convert ISO 8601 timestamp to readable local format."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %I:%M:%S %p")
    except (ValueError, TypeError):
        return iso_str


def fmt_retrieved(dt: object) -> str:
    """Format the retrieval datetime for the status bar."""
    if isinstance(dt, datetime):
        local = dt.astimezone()
        return local.strftime("%b %d, %I:%M:%S %p")
    return str(dt)


def fmt_change(quote: Quote) -> str:
    """Format daily price change as '+1.23 (+0.5%)' or '-1.23 (-0.5%)'."""
    if quote.last_trade_price is None or quote.open_price is None:
        return "---"
    change = quote.last_trade_price - quote.open_price
    pct = change / quote.open_price * 100 if quote.open_price != 0 else 0.0
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:,.2f} ({sign}{pct:.2f}%)"


def get_change_value(quote: Quote) -> float | None:
    """Return the raw price change, or None if unavailable."""
    if quote.last_trade_price is None or quote.open_price is None:
        return None
    return quote.last_trade_price - quote.open_price


def fmt_status(quote: Quote) -> str:
    """Format the real-time/delayed/halted status string."""
    if quote.is_halted:
        return "HALTED"
    if quote.delay > 0:
        return f"Delayed {quote.delay}m"
    return "Real-Time"


def fmt_sparkline(history: list[float]) -> str:
    """Convert a list of price values to a Unicode sparkline string."""
    if len(history) < 2:
        return ""
    lo, hi = min(history), max(history)
    if hi == lo:
        return _SPARK_CHARS[3] * len(history)
    scale = len(_SPARK_CHARS) - 1
    return "".join(
        _SPARK_CHARS[int((v - lo) / (hi - lo) * scale)] for v in history
    )


def sort_key_for_column(quote: Quote, column: str) -> tuple[int, float | str]:
    """Return a sortable key for the given column. None values sort last."""
    # Compute spread for sorting
    _spread: float | None = None
    if quote.bid_price is not None and quote.ask_price is not None:
        _spread = quote.ask_price - quote.bid_price
    _col_map: dict[str, object] = {
        "symbol": quote.symbol,
        "last_price": quote.last_trade_price,
        "change": get_change_value(quote),
        "bid": quote.bid_price,
        "ask": quote.ask_price,
        "spread": _spread,
        "high": quote.high_price,
        "low": quote.low_price,
        "volume": quote.volume,
        "last_trade": quote.last_trade_time,
        "status": 0 if quote.is_halted else (1 if quote.delay > 0 else 2),
        "trend": "",
    }
    val = _col_map.get(column, quote.symbol)
    if val is None:
        return (1, 0.0)
    if isinstance(val, str):
        return (0, val)
    return (0, float(val))
