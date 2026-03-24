"""Console output formatting for quote results."""
from __future__ import annotations

from datetime import datetime, timezone

from questrade.models.quote import Quote

_LINE = "━" * 75


def print_quote_table(quotes: list[Quote], retrieved_at: datetime) -> None:
    """Print a formatted results table for a list of quotes.

    Args:
        quotes: List of Quote objects from the Questrade API.
        retrieved_at: UTC datetime when the API call was made.
    """
    utc_ts = retrieved_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"\n{_LINE}")
    print(f" QUESTRADE LIVE QUOTES  |  Retrieved: {utc_ts}")
    print(_LINE)

    for quote in quotes:
        price_str = (
            f"${quote.last_trade_price:.2f}"
            if quote.last_trade_price is not None
            else "N/A — no trades recorded"
        )

        trade_time = _format_trade_time(quote.last_trade_time)
        data_status = f"⚠️  Delayed {quote.delay}m" if quote.delay > 0 else "Real-Time    "
        halt_status = "🔴 HALTED" if quote.is_halted else "✅ Active"

        print(
            f" {quote.symbol:<6}"
            f"| {price_str:<12}"
            f"| {trade_time:<22}"
            f"| {data_status:<16}"
            f"| {halt_status}"
        )

    print(f"{_LINE}\n")

    # Surface aggregate warnings below the table
    delayed = [q.symbol for q in quotes if q.delay > 0]
    if delayed:
        print(
            f"⚠️  Delayed data: {', '.join(delayed)}. "
            "Subscribe to Level 1 real-time data for live quotes."
        )

    halted = [q.symbol for q in quotes if q.is_halted]
    if halted:
        print(f"🔴 Trading halted: {', '.join(halted)}.")


def _format_trade_time(iso_time: str) -> str:
    """Parse an ISO 8601 timestamp and format for display (ET local time).

    Args:
        iso_time: ISO 8601 string from the Questrade API.

    Returns:
        Human-readable string, or the raw string if parsing fails.
    """
    try:
        dt = datetime.fromisoformat(iso_time)
        return dt.strftime("%Y-%m-%d %I:%M %p ET")
    except (ValueError, TypeError):
        return iso_time or "N/A"
