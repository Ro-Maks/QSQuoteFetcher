"""Tkinter GUI for the Questrade Price Fetcher."""
from __future__ import annotations

import ctypes
import logging
import threading
import tkinter as tk
from tkinter import ttk

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


def _fmt_price(value: float | None) -> str:
    return f"${value:.2f}" if value is not None else "N/A"


def _fmt_volume(volume: int) -> str:
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M"
    if volume >= 1_000:
        return f"{volume / 1_000:.1f}K"
    return str(volume)


def _fmt_status(quote: Quote) -> str:
    if quote.is_halted:
        return "HALTED"
    if quote.delay > 0:
        return f"Delayed {quote.delay}m"
    return "Real-Time"


class QuoteApp(tk.Tk):
    """Main application window displaying live Questrade quotes."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Questrade Quote Fetcher")
        self.minsize(780, 250)
        self._build_ui()
        # Fetch quotes on startup.
        self.after(100, self._refresh_quotes)

    def _build_ui(self) -> None:
        # --- Header ---
        header = ttk.Frame(self, padding=10)
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="Questrade Live Quotes",
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT)

        self._refresh_btn = ttk.Button(
            header, text="Refresh", command=self._refresh_quotes,
        )
        self._refresh_btn.pack(side=tk.RIGHT)

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
            "symbol": 80,
            "last_price": 100,
            "bid": 90,
            "ask": 90,
            "volume": 90,
            "last_trade": 180,
            "status": 100,
        }
        for col in columns:
            self._tree.heading(col, text=headings[col])
            self._tree.column(col, width=widths[col], anchor=tk.CENTER)

        self._tree.tag_configure("halted", foreground="red")
        self._tree.tag_configure("delayed", foreground="orange")
        self._tree.pack(fill=tk.BOTH, expand=True, padx=10)

        # --- Status bar ---
        status_frame = ttk.Frame(self, padding=(10, 5))
        status_frame.pack(fill=tk.X)

        self._time_label = ttk.Label(status_frame, text="")
        self._time_label.pack(side=tk.LEFT)

        self._status_label = ttk.Label(status_frame, text="")
        self._status_label.pack(side=tk.RIGHT)

    def _refresh_quotes(self) -> None:
        self._refresh_btn.configure(state=tk.DISABLED)
        self._status_label.configure(text="Fetching...", foreground="")
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

            self._tree.insert("", tk.END, values=(
                quote.symbol,
                _fmt_price(quote.last_trade_price),
                _fmt_price(quote.bid_price),
                _fmt_price(quote.ask_price),
                _fmt_volume(quote.volume),
                quote.last_trade_time,
                _fmt_status(quote),
            ), tags=(tag,))

        self._time_label.configure(text=f"Retrieved: {retrieved_at}")
        self._status_label.configure(text="OK", foreground="green")
        self._refresh_btn.configure(state=tk.NORMAL)

    def _on_fetch_error(self, message: str) -> None:
        self._status_label.configure(text=message, foreground="red")
        self._refresh_btn.configure(state=tk.NORMAL)


def main() -> None:
    """Launch the GUI application."""
    app = QuoteApp()
    app.mainloop()


if __name__ == "__main__":
    main()
