"""Tkinter GUI for the Questrade Price Fetcher (ttkbootstrap themed)."""
from __future__ import annotations

import ctypes
import threading
import tkinter as tk
from datetime import datetime, timezone

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, END, LEFT, NORMAL, RIGHT, X, Y, BOTTOM, TOP, W, E

from questrade.main import fetch_all_quotes
from questrade.models.errors import (
    QuestradeApiError,
    QuoteUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
    TokenRefreshError,
)
from questrade.models.quote import Quote

# Enable DPI awareness on Windows for crisp rendering.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass

AUTO_REFRESH_INTERVAL = 10  # seconds

# -- Color palette --
CLR_BG_DARK = "#1a1d23"
CLR_BG_HEADER = "#21252b"
CLR_BG_CARD = "#282c34"
CLR_BG_ROW_ALT = "#2c313a"
CLR_ACCENT = "#61afef"
CLR_GREEN = "#98c379"
CLR_RED = "#e06c75"
CLR_ORANGE = "#e5c07b"
CLR_TEXT = "#abb2bf"
CLR_TEXT_BRIGHT = "#d4d7dd"
CLR_TEXT_DIM = "#636d83"
CLR_BORDER = "#3e4451"

FONT_FAMILY = "Segoe UI"


def _fmt_price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "---"


def _fmt_volume(volume: int) -> str:
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:,.1f}M"
    if volume >= 1_000:
        return f"{volume / 1_000:,.1f}K"
    return f"{volume:,}"


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
        return local.strftime("%b %d, %I:%M:%S %p")
    return str(dt)


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
        self.minsize(900, 400)
        self.geometry("960x500")
        self._auto_refresh_on = False
        self._countdown = 0
        self._countdown_timer_id: str | None = None
        self._quote_count = 0

        self.configure(background=CLR_BG_DARK)
        self._configure_styles()
        self._build_ui()
        # Fetch quotes on startup.
        self.after(100, self._refresh_quotes)

    def _configure_styles(self) -> None:
        style = ttk.Style()

        style.configure(
            "Header.TFrame",
            background=CLR_BG_HEADER,
        )
        style.configure(
            "Card.TFrame",
            background=CLR_BG_CARD,
        )
        style.configure(
            "Dark.TFrame",
            background=CLR_BG_DARK,
        )
        style.configure(
            "Title.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_BRIGHT,
            font=(FONT_FAMILY, 18, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "StatusDot.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_GREEN,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "StatusBar.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "StatusOk.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_GREEN,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "StatusError.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_RED,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "Countdown.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_ACCENT,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "Fetching.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_ACCENT,
            font=(FONT_FAMILY, 11),
        )

        # Treeview styling
        style.configure(
            "Custom.Treeview",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT,
            fieldbackground=CLR_BG_CARD,
            borderwidth=0,
            font=(FONT_FAMILY, 10),
            rowheight=36,
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            borderwidth=0,
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
        )
        style.map(
            "Custom.Treeview.Heading",
            background=[("active", CLR_BG_HEADER)],
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#3e4451")],
            foreground=[("selected", CLR_TEXT_BRIGHT)],
        )

        # Buttons
        style.configure(
            "Refresh.TButton",
            font=(FONT_FAMILY, 10),
            padding=(16, 8),
        )
        style.configure(
            "AutoRefresh.TButton",
            font=(FONT_FAMILY, 10),
            padding=(14, 8),
        )

        # Progress bar for countdown
        style.configure(
            "TProgressbar",
            troughcolor=CLR_BG_DARK,
            thickness=3,
        )

    def _build_ui(self) -> None:
        # --- Header ---
        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 16))
        header.pack(fill=X)

        title_area = ttk.Frame(header, style="Header.TFrame")
        title_area.pack(side=LEFT)

        ttk.Label(title_area, text="Questrade Live Quotes", style="Title.TLabel").pack(
            side=LEFT, anchor=W
        )

        self._dot_label = ttk.Label(title_area, text="  \u2022 Connected", style="StatusDot.TLabel")
        self._dot_label.pack(side=LEFT, padx=(12, 0))

        btn_area = ttk.Frame(header, style="Header.TFrame")
        btn_area.pack(side=RIGHT)

        self._auto_btn = ttk.Button(
            btn_area,
            text="\u21bb  Auto: OFF",
            command=self._toggle_auto_refresh,
            bootstyle="secondary-outline",  # type: ignore[arg-type]
            style="AutoRefresh.TButton",
        )
        self._auto_btn.pack(side=RIGHT, padx=(8, 0))

        self._refresh_btn = ttk.Button(
            btn_area,
            text="\u27f3  Refresh",
            command=self._refresh_quotes,
            bootstyle="info",  # type: ignore[arg-type]
            style="Refresh.TButton",
        )
        self._refresh_btn.pack(side=RIGHT)

        # --- Thin accent line under header ---
        accent_line = tk.Frame(self, background=CLR_ACCENT, height=2)
        accent_line.pack(fill=X)

        # --- Table area ---
        table_frame = ttk.Frame(self, style="Dark.TFrame", padding=(16, 12, 16, 0))
        table_frame.pack(fill=BOTH, expand=True)

        columns = ("symbol", "last_price", "bid", "ask", "volume", "last_trade", "status")
        self._tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="browse",
        )

        headings = {
            "symbol": "SYMBOL",
            "last_price": "LAST PRICE",
            "bid": "BID",
            "ask": "ASK",
            "volume": "VOLUME",
            "last_trade": "LAST TRADE",
            "status": "STATUS",
        }
        col_config = {
            "symbol":     {"width": 100, "minwidth": 70,  "anchor": W},
            "last_price": {"width": 110, "minwidth": 90,  "anchor": E},
            "bid":        {"width": 100, "minwidth": 80,  "anchor": E},
            "ask":        {"width": 100, "minwidth": 80,  "anchor": E},
            "volume":     {"width": 100, "minwidth": 70,  "anchor": E},
            "last_trade": {"width": 180, "minwidth": 140, "anchor": tk.CENTER},
            "status":     {"width": 110, "minwidth": 90,  "anchor": tk.CENTER},
        }
        for col in columns:
            self._tree.heading(col, text=headings[col])
            cfg = col_config[col]
            self._tree.column(col, width=cfg["width"], minwidth=cfg["minwidth"], anchor=cfg["anchor"])

        self._tree.tag_configure("halted", foreground=CLR_RED)
        self._tree.tag_configure("delayed", foreground=CLR_ORANGE)
        self._tree.tag_configure("stripe", background=CLR_BG_ROW_ALT)
        self._tree.tag_configure("halted_stripe", foreground=CLR_RED, background=CLR_BG_ROW_ALT)
        self._tree.tag_configure("delayed_stripe", foreground=CLR_ORANGE, background=CLR_BG_ROW_ALT)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # --- Countdown progress bar ---
        self._progress = ttk.Progressbar(
            self,
            bootstyle="info",  # type: ignore[arg-type]
            maximum=AUTO_REFRESH_INTERVAL,
            mode="determinate",
        )
        # Starts hidden; shown when auto-refresh is active.

        # --- Status bar ---
        separator = ttk.Separator(self)
        separator.pack(fill=X, padx=16, pady=(8, 0))

        status_frame = ttk.Frame(self, style="Dark.TFrame", padding=(20, 8, 20, 12))
        status_frame.pack(fill=X)

        self._time_label = ttk.Label(status_frame, text="", style="StatusBar.TLabel")
        self._time_label.pack(side=LEFT)

        self._status_label = ttk.Label(status_frame, text="", style="StatusBar.TLabel")
        self._status_label.pack(side=RIGHT)

        self._countdown_label = ttk.Label(status_frame, text="", style="Countdown.TLabel")
        self._countdown_label.pack(side=RIGHT, padx=(0, 16))

    # --- Auto-refresh ---

    def _toggle_auto_refresh(self) -> None:
        self._auto_refresh_on = not self._auto_refresh_on
        if self._auto_refresh_on:
            self._auto_btn.configure(
                text="\u21bb  Auto: ON",
                bootstyle="success",  # type: ignore[arg-type]
            )
            self._start_countdown()
        else:
            self._auto_btn.configure(
                text="\u21bb  Auto: OFF",
                bootstyle="secondary-outline",  # type: ignore[arg-type]
            )
            self._cancel_countdown()
            self._countdown_label.configure(text="")
            self._progress.pack_forget()

    def _start_countdown(self) -> None:
        self._countdown = AUTO_REFRESH_INTERVAL
        self._progress.configure(value=AUTO_REFRESH_INTERVAL)
        self._progress.pack(fill=X, padx=16, pady=(4, 0), before=self._get_separator())
        self._tick_countdown()

    def _get_separator(self) -> tk.Widget:
        """Return the separator widget for insertion ordering."""
        for child in self.winfo_children():
            if isinstance(child, ttk.Separator):
                return child
        return self.winfo_children()[-1]

    def _tick_countdown(self) -> None:
        if not self._auto_refresh_on:
            return
        if self._countdown <= 0:
            self._progress.pack_forget()
            self._refresh_quotes()
            return
        self._countdown_label.configure(text=f"Next refresh in {self._countdown}s")
        self._progress.configure(value=self._countdown)
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
        self._status_label.configure(text="\u27f3 Fetching\u2026", style="StatusBar.TLabel")
        self._countdown_label.configure(text="")
        self._progress.pack_forget()

        self._dot_label.configure(text="  \u2022 Fetching\u2026", foreground=CLR_ACCENT)
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

        for i, quote in enumerate(quotes):
            is_stripe = i % 2 == 1

            if quote.is_halted:
                tag = "halted_stripe" if is_stripe else "halted"
            elif quote.delay > 0:
                tag = "delayed_stripe" if is_stripe else "delayed"
            elif is_stripe:
                tag = "stripe"
            else:
                tag = ""

            status_text = _fmt_status(quote)

            self._tree.insert("", END, values=(
                f"  {quote.symbol}",
                _fmt_price(quote.last_trade_price),
                _fmt_price(quote.bid_price),
                _fmt_price(quote.ask_price),
                _fmt_volume(quote.volume),
                _fmt_time(quote.last_trade_time),
                status_text,
            ), tags=(tag,) if tag else ())

        self._quote_count = len(quotes)
        self._time_label.configure(
            text=f"Last updated: {_fmt_retrieved(retrieved_at)}  \u2022  {self._quote_count} symbols"
        )
        self._status_label.configure(text="\u2713 OK", style="StatusOk.TLabel")
        self._refresh_btn.configure(state=NORMAL)
        self._dot_label.configure(text="  \u2022 Connected", foreground=CLR_GREEN)

        # Restart countdown if auto-refresh is on.
        if self._auto_refresh_on:
            self._start_countdown()

    def _on_fetch_error(self, message: str) -> None:
        self._status_label.configure(text=message, style="StatusError.TLabel")
        self._refresh_btn.configure(state=NORMAL)
        self._dot_label.configure(text="  \u2022 Error", foreground=CLR_RED)

        # Keep auto-refreshing even after errors.
        if self._auto_refresh_on:
            self._start_countdown()


def main() -> None:
    """Launch the GUI application."""
    app = QuoteApp()
    app.mainloop()


if __name__ == "__main__":
    main()
