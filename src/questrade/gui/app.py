"""Main application window composing all GUI components."""
from __future__ import annotations

import contextlib
import ctypes
import threading
import tkinter as tk
from datetime import datetime

import ttkbootstrap as ttk
from ttkbootstrap.constants import X

from questrade.gui.detail import DetailPanel
from questrade.gui.dialogs import open_symbol_manager
from questrade.gui.formatting import fmt_retrieved
from questrade.gui.header import HeaderFrame
from questrade.gui.statusbar import StatusBar
from questrade.gui.styles import (
    CLR_ACCENT,
    CLR_BG_CARD,
    CLR_BG_DARK,
    CLR_TEXT,
    DEFAULT_REFRESH_INTERVAL,
    configure_styles,
)
from questrade.gui.table import QuoteTable
from questrade.gui.tray import SystemTray
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
with contextlib.suppress(Exception):
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[union-attr]


class QuoteApp(ttk.Window):
    """Main application window displaying live Questrade quotes."""

    def __init__(self) -> None:
        super().__init__(title="Questrade Quote Fetcher", themename="darkly")
        self.minsize(1060, 450)

        # Load persisted settings
        from questrade.config import load_settings

        self._settings = load_settings()
        self.geometry(str(self._settings.get("window_geometry", "1200x500")))

        # State
        self._auto_refresh_on = False
        self._countdown = 0
        self._countdown_timer_id: str | None = None
        self._quote_count = 0
        self._refresh_interval: int = int(
            self._settings.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
        )
        self._sort_column: str = str(self._settings.get("sort_column", "symbol"))
        self._sort_descending: bool = bool(self._settings.get("sort_descending", False))
        self._quotes: list[Quote] = []
        self._retrieved_at: object = None
        self._price_history: dict[str, list[float]] = {}
        self._selected_symbol: str | None = None

        self.configure(background=CLR_BG_DARK)
        self.option_add("*TCombobox*Listbox.background", CLR_BG_CARD)
        self.option_add("*TCombobox*Listbox.foreground", CLR_TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", CLR_ACCENT)

        configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self._header.update_market_status()

        # Restore auto-refresh from settings
        if self._settings.get("auto_refresh", False):
            self.toggle_auto_refresh()

        # System tray
        self._tray = SystemTray(self)
        self._tray.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", self._on_minimize)
        self.after(100, self.refresh_quotes)

    def _build_ui(self) -> None:
        # Header
        self._header = HeaderFrame(self)
        self._header.pack(fill=X)

        # Accent line
        tk.Frame(self, background=CLR_ACCENT, height=2).pack(fill=X)

        # Quote table
        self._table = QuoteTable(self)
        self._table.pack(fill=tk.BOTH, expand=True)

        # Detail panel (hidden initially)
        self._detail = DetailPanel(self)

        # Countdown progress bar (hidden initially)
        self._progress = ttk.Progressbar(
            self,
            bootstyle="info",  # type: ignore[arg-type]
            maximum=self._refresh_interval,
            mode="determinate",
        )

        # Separator + Status bar
        self._separator = ttk.Separator(self)
        self._separator.pack(fill=X, padx=16, pady=(8, 0))

        self._statusbar = StatusBar(self)
        self._statusbar.pack(fill=X)

    def _bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        self.bind("<F5>", lambda _e: self.refresh_quotes())
        self.bind("<Control-r>", lambda _e: self.refresh_quotes())
        self.bind("<Escape>", lambda _e: self._hide_detail_panel())
        self.bind("<Control-m>", lambda _e: self.open_symbol_manager())

    # -- Public callbacks (called by child components) --

    def get_price_history(self, symbol: str) -> list[float]:
        """Return the price history for a symbol (used by tooltip)."""
        return self._price_history.get(symbol, [])

    def refresh_quotes(self) -> None:
        """Trigger a quote refresh."""
        self._cancel_countdown()
        self._header.set_refresh_enabled(False)
        self._statusbar.set_status("\u27f3 Fetching\u2026", "StatusBar.TLabel")
        self._statusbar.set_countdown("")
        self._progress.pack_forget()
        self._header.set_status_fetching()
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def toggle_auto_refresh(self) -> None:
        """Toggle automatic refresh on/off."""
        self._auto_refresh_on = not self._auto_refresh_on
        self._header.set_auto_refresh_display(self._auto_refresh_on)
        if self._auto_refresh_on:
            self._start_countdown()
        else:
            self._cancel_countdown()
            self._statusbar.set_countdown("")
            self._progress.pack_forget()

    def set_refresh_interval(self, seconds: int) -> None:
        """Update the refresh interval."""
        self._refresh_interval = seconds
        self._progress.configure(maximum=seconds)
        if self._auto_refresh_on:
            self._cancel_countdown()
            self._start_countdown()

    def open_symbol_manager(self) -> None:
        """Open the symbol management dialog."""
        open_symbol_manager(self)

    def on_symbols_saved(self, current_symbols: list[object]) -> None:
        """Handle symbol list update from the dialog."""
        from questrade.models.symbol import SymbolConfig

        valid = {s.symbol for s in current_symbols if isinstance(s, SymbolConfig)}
        for k in [k for k in self._price_history if k not in valid]:
            del self._price_history[k]
        if self._selected_symbol and self._selected_symbol not in valid:
            self._hide_detail_panel()
        self.refresh_quotes()

    def on_sort(self, column: str) -> None:
        """Handle column sort request."""
        if column == self._sort_column:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_column = column
            self._sort_descending = False
        if self._quotes:
            self._sort_and_display()

    def on_row_selected(self, symbol: str) -> None:
        """Handle row selection from the table."""
        if symbol == self._selected_symbol:
            self._hide_detail_panel()
            return
        self._selected_symbol = symbol
        self._show_detail_panel(symbol)

    def show_detail_for(self, symbol: str) -> None:
        """Show the detail panel for a symbol (called during repopulate)."""
        self._show_detail_panel(symbol)

    # -- Auto-refresh countdown --

    def _start_countdown(self) -> None:
        self._countdown = self._refresh_interval
        self._progress.configure(value=self._refresh_interval)
        self._progress.pack(fill=X, padx=16, pady=(4, 0), before=self._separator)
        self._tick_countdown()

    def _tick_countdown(self) -> None:
        if not self._auto_refresh_on:
            return
        if self._countdown <= 0:
            self._progress.pack_forget()
            self.refresh_quotes()
            return
        self._statusbar.set_countdown(f"Next refresh in {self._countdown}s")
        self._progress.configure(value=self._countdown)
        self._countdown -= 1
        self._countdown_timer_id = self.after(1000, self._tick_countdown)

    def _cancel_countdown(self) -> None:
        if self._countdown_timer_id is not None:
            self.after_cancel(self._countdown_timer_id)
            self._countdown_timer_id = None

    # -- Fetching --

    def _fetch_worker(self) -> None:
        try:
            quotes, retrieved_at = fetch_all_quotes()
            self.after(0, self._on_fetch_complete, quotes, retrieved_at)
        except (
            OSError,
            TokenRefreshError,
            SymbolNotFoundError,
            QuoteUnavailableError,
            RateLimitError,
            QuestradeApiError,
        ) as exc:
            self.after(0, self._on_fetch_error, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_fetch_error, f"Unexpected error: {exc}")

    def _on_fetch_complete(self, quotes: list[Quote], retrieved_at: object) -> None:
        self._quotes = quotes
        self._retrieved_at = retrieved_at

        for q in quotes:
            if q.last_trade_price is not None:
                hist = self._price_history.setdefault(q.symbol, [])
                hist.append(q.last_trade_price)
                if len(hist) > 20:
                    hist.pop(0)

        self._sort_and_display()

        self._quote_count = len(quotes)
        self._statusbar.set_time_text(
            f"Last updated: {fmt_retrieved(retrieved_at)}  \u2022  {self._quote_count} symbols",
        )
        if isinstance(retrieved_at, datetime):
            self._header.set_updated_time(retrieved_at.astimezone().strftime("%I:%M:%S %p"))
        self._statusbar.set_status("\u2713 OK", "StatusOk.TLabel")
        self._header.set_refresh_enabled(True)
        self._header.set_status_connected()

        # Check for big moves and send notifications
        self._tray.check_alerts()

    def _on_fetch_error(self, message: str) -> None:
        self._statusbar.set_status(message, "StatusError.TLabel")
        self._header.set_refresh_enabled(True)
        self._header.set_status_error()
        if self._auto_refresh_on:
            self._start_countdown()

    # -- Sorting & display --

    def _sort_and_display(self) -> None:
        self._table.populate(
            self._quotes,
            self._sort_column,
            self._sort_descending,
            self._price_history,
            self._selected_symbol,
        )
        if self._auto_refresh_on:
            self._start_countdown()

    # -- Detail panel --

    def _show_detail_panel(self, symbol: str) -> None:
        quote = next((q for q in self._quotes if q.symbol == symbol), None)
        if quote is None:
            return

        from questrade.config import TARGET_SYMBOLS

        name = next((s.name for s in TARGET_SYMBOLS if s.symbol == symbol), symbol)
        history = self._price_history.get(symbol, [])
        self._detail.show(quote, name, history, self._table)

    def _hide_detail_panel(self) -> None:
        self._selected_symbol = None
        self._detail.hide()
        self._table.clear_selection()

    # -- Settings persistence --

    def _on_minimize(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Minimize to system tray instead of taskbar."""
        if event.widget == self and self.state() == "iconic":
            self.withdraw()

    def _on_close(self) -> None:
        """Save settings, stop tray, and close the application."""
        from questrade.config import save_settings

        self._tray.stop()
        self._settings.update({
            "window_geometry": self.geometry(),
            "sort_column": self._sort_column,
            "sort_descending": self._sort_descending,
            "auto_refresh": self._auto_refresh_on,
            "refresh_interval": self._refresh_interval,
        })
        save_settings(self._settings)
        self.destroy()
