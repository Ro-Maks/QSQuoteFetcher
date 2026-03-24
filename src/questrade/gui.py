"""Tkinter GUI for the Questrade Price Fetcher (ttkbootstrap themed)."""
from __future__ import annotations

import ctypes
import logging
import threading
import tkinter as tk
from datetime import datetime, timezone

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, END, LEFT, NORMAL, RIGHT, X

from questrade.main import fetch_all_quotes
from questrade.models.errors import (
    QuestradeApiError,
    QuoteUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
    TokenRefreshError,
)
from questrade.models.quote import Quote

logger = logging.getLogger(__name__)

# Enable DPI awareness on Windows for crisp rendering.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass

AUTO_REFRESH_INTERVAL = 10  # seconds


def _fmt_price(value: float | None) -> str:
    return f"${value:.2f}" if value is not None else "N/A"


def _fmt_volume(volume: int) -> str:
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M"
    if volume >= 1_000:
        return f"{volume / 1_000:.1f}K"
    return str(volume)


def _fmt_time(iso_str: str) -> str:
    """Convert ISO 8601 timestamp to readable local format."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %I:%M %p")
    except (ValueError, TypeError):
        return iso_str


def _fmt_retrieved(dt: object) -> str:
    """Format the retrieval datetime for the status bar."""
    if isinstance(dt, datetime):
        local = dt.astimezone()
        return f"Retrieved: {local.strftime('%b %d, %I:%M:%S %p')}"
    return f"Retrieved: {dt}"


def _fmt_status(quote: Quote) -> str:
    if quote.is_halted:
        return "HALTED"
    if quote.delay > 0:
        return f"Delayed {quote.delay}m"
    return "Real-Time"


class QuoteApp(ttk.Window):
    """Main application window displaying live Questrade quotes."""

    def __init__(self) -> None:
        super().__init__(title="Questrade Quote Fetcher", themename="darkly")
        self.minsize(800, 280)
        self._auto_refresh_on = False
        self._countdown = 0
        self._countdown_timer_id: str | None = None
        self._build_ui()
        # Fetch quotes on startup.
        self.after(100, self._refresh_quotes)

    def _build_ui(self) -> None:
        # --- Header ---
        header = ttk.Frame(self, padding=10)
        header.pack(fill=X)

        ttk.Label(
            header,
            text="Questrade Live Quotes",
            font=("Segoe UI", 16, "bold"),
        ).pack(side=LEFT)

        self._refresh_btn = ttk.Button(
            header,
            text="Refresh",
            command=self._refresh_quotes,
            bootstyle="primary",  # type: ignore[arg-type]
        )
        self._refresh_btn.pack(side=RIGHT, padx=(5, 0))

        self._auto_btn = ttk.Button(
            header,
            text="Auto-Refresh: OFF",
            command=self._toggle_auto_refresh,
            bootstyle="secondary-outline",  # type: ignore[arg-type]
        )
        self._auto_btn.pack(side=RIGHT)

        # --- Table ---
        columns = ("symbol", "last_price", "bid", "ask", "volume", "last_trade", "status")
        self._tree = ttk.Treeview(self, columns=columns, show="headings", height=5)

        headings = {
            "symbol": "Symbol",
            "last_price": "Last Price",
            "bid": "Bid",
            "ask": "Ask",
            "volume": "Volume",
            "last_trade": "Last Trade",
            "status": "Status",
        }
        widths = {
            "symbol": 90,
            "last_price": 100,
            "bid": 90,
            "ask": 90,
            "volume": 90,
            "last_trade": 190,
            "status": 100,
        }
        for col in columns:
            self._tree.heading(col, text=headings[col])
            self._tree.column(col, width=widths[col], anchor=tk.CENTER)

        self._tree.tag_configure("halted", foreground="#e74c3c")
        self._tree.tag_configure("delayed", foreground="#f39c12")
        self._tree.pack(fill=BOTH, expand=True, padx=10)

        # --- Status bar ---
        status_frame = ttk.Frame(self, padding=(10, 5))
        status_frame.pack(fill=X)

        self._time_label = ttk.Label(status_frame, text="", font=("Segoe UI", 9))
        self._time_label.pack(side=LEFT)

        self._status_label = ttk.Label(status_frame, text="", font=("Segoe UI", 9))
        self._status_label.pack(side=RIGHT)

        self._countdown_label = ttk.Label(status_frame, text="", font=("Segoe UI", 9))
        self._countdown_label.pack(side=RIGHT, padx=(0, 15))

    # --- Auto-refresh ---

    def _toggle_auto_refresh(self) -> None:
        self._auto_refresh_on = not self._auto_refresh_on
        if self._auto_refresh_on:
            self._auto_btn.configure(
                text="Auto-Refresh: ON",
                bootstyle="success",  # type: ignore[arg-type]
            )
            self._start_countdown()
        else:
            self._auto_btn.configure(
                text="Auto-Refresh: OFF",
                bootstyle="secondary-outline",  # type: ignore[arg-type]
            )
            self._cancel_countdown()
            self._countdown_label.configure(text="")

    def _start_countdown(self) -> None:
        self._countdown = AUTO_REFRESH_INTERVAL
        self._tick_countdown()

    def _tick_countdown(self) -> None:
        if not self._auto_refresh_on:
            return
        if self._countdown <= 0:
            self._refresh_quotes()
            return
        self._countdown_label.configure(text=f"Next refresh: {self._countdown}s")
        self._countdown -= 1
        self._countdown_timer_id = self.after(1000, self._tick_countdown)

    def _cancel_countdown(self) -> None:
        if self._countdown_timer_id is not None:
            self.after_cancel(self._countdown_timer_id)
            self._countdown_timer_id = None

    # --- Fetching ---

    def _refresh_quotes(self) -> None:
        self._cancel_countdown()
        self._refresh_btn.configure(state=DISABLED)
        self._status_label.configure(text="Fetching...", foreground="")
        self._countdown_label.configure(text="")
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self) -> None:
        try:
            quotes, retrieved_at = fetch_all_quotes()
            self.after(0, self._on_fetch_complete, quotes, retrieved_at)
        except (
            TokenRefreshError,
            SymbolNotFoundError,
            QuoteUnavailableError,
            RateLimitError,
            QuestradeApiError,
            EnvironmentError,
        ) as exc:
            self.after(0, self._on_fetch_error, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_fetch_error, f"Unexpected error: {exc}")

    def _on_fetch_complete(self, quotes: list[Quote], retrieved_at: object) -> None:
        # Clear existing rows.
        for item in self._tree.get_children():
            self._tree.delete(item)

        for quote in quotes:
            tag = ""
            if quote.is_halted:
                tag = "halted"
            elif quote.delay > 0:
                tag = "delayed"

            self._tree.insert("", END, values=(
                quote.symbol,
                _fmt_price(quote.last_trade_price),
                _fmt_price(quote.bid_price),
                _fmt_price(quote.ask_price),
                _fmt_volume(quote.volume),
                _fmt_time(quote.last_trade_time),
                _fmt_status(quote),
            ), tags=(tag,))

        self._time_label.configure(text=_fmt_retrieved(retrieved_at))
        self._status_label.configure(text="OK", foreground="#2ecc71")
        self._refresh_btn.configure(state=NORMAL)

        # Restart countdown if auto-refresh is on.
        if self._auto_refresh_on:
            self._start_countdown()

    def _on_fetch_error(self, message: str) -> None:
        self._status_label.configure(text=message, foreground="#e74c3c")
        self._refresh_btn.configure(state=NORMAL)

        # Keep auto-refreshing even after errors.
        if self._auto_refresh_on:
            self._start_countdown()


def main() -> None:
    """Launch the GUI application."""
    app = QuoteApp()
    app.mainloop()


if __name__ == "__main__":
    main()
