"""Header bar: title, connection status, market status, action buttons."""
from __future__ import annotations

import tkinter as tk
from datetime import UTC, datetime, timedelta, timezone
from datetime import time as dt_time
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap.constants import LEFT, RIGHT, W

from questrade.gui.styles import (
    CLR_ACCENT,
    CLR_GREEN,
    CLR_RED,
    DEFAULT_REFRESH_INTERVAL,
    REFRESH_INTERVALS,
)

if TYPE_CHECKING:
    from questrade.gui.app import QuoteApp

_UTC_OFFSET_EST = timezone(timedelta(hours=-5))
_UTC_OFFSET_EDT = timezone(timedelta(hours=-4))


def _now_eastern() -> datetime:
    """Return the current time in US Eastern, accounting for DST.

    DST (EDT, UTC-4) runs from the second Sunday in March at 2 AM
    to the first Sunday in November at 2 AM; otherwise EST (UTC-5).
    """
    utc_now = datetime.now(UTC)
    year = utc_now.year
    mar1_wd = datetime(year, 3, 1).weekday()
    second_sun_mar = 8 + (6 - mar1_wd) % 7
    dst_start = datetime(year, 3, second_sun_mar, 7, tzinfo=UTC)
    nov1_wd = datetime(year, 11, 1).weekday()
    first_sun_nov = 1 + (6 - nov1_wd) % 7
    dst_end = datetime(year, 11, first_sun_nov, 6, tzinfo=UTC)
    tz = _UTC_OFFSET_EDT if dst_start <= utc_now < dst_end else _UTC_OFFSET_EST
    return utc_now.astimezone(tz)


def _get_market_status() -> tuple[str, str]:
    """Return (display_text, style_name) for the current US market session."""
    now = _now_eastern()
    if now.weekday() >= 5:
        return ("Market Closed", "Mkc.TLabel")
    t = now.time()
    if t < dt_time(4, 0):
        return ("Market Closed", "Mkc.TLabel")
    if t < dt_time(9, 30):
        return ("Pre-Market", "Mkx.TLabel")
    if t < dt_time(16, 0):
        return ("Market Open", "Mko.TLabel")
    if t < dt_time(20, 0):
        return ("After-Hours", "Mkx.TLabel")
    return ("Market Closed", "Mkc.TLabel")


class HeaderFrame(ttk.Frame):
    """Top header bar with title, status, and action buttons."""

    def __init__(self, parent: QuoteApp) -> None:
        super().__init__(parent, style="Header.TFrame", padding=(20, 16))
        self._app = parent
        self._fetching = False
        self._pulse_id: str | None = None
        self._build()

    def _build(self) -> None:
        title_area = ttk.Frame(self, style="Header.TFrame")
        title_area.pack(side=LEFT)

        ttk.Label(title_area, text="Questrade Live Quotes", style="Title.TLabel").pack(
            side=LEFT, anchor=W,
        )

        self._dot_label = ttk.Label(title_area, text="  \u2022 Connected", style="StatusDot.TLabel")
        self._dot_label.pack(side=LEFT, padx=(12, 0))

        ttk.Label(title_area, text="  \u2022", style="Subtitle.TLabel").pack(side=LEFT)
        self._market_status_label = ttk.Label(title_area, text="", style="Mkc.TLabel")
        self._market_status_label.pack(side=LEFT, padx=(4, 0))

        btn_area = ttk.Frame(self, style="Header.TFrame")
        btn_area.pack(side=RIGHT)

        # Last-updated display
        updated_area = ttk.Frame(self, style="Header.TFrame")
        updated_area.pack(side=RIGHT, padx=(0, 20))

        ttk.Label(updated_area, text="Last Updated  ", style="Refreshlbl.TLabel").pack(side=LEFT)
        self._updated_label = ttk.Label(updated_area, text="--:--:-- --", style="Refreshval.TLabel")
        self._updated_label.pack(side=LEFT)

        self._manage_btn = ttk.Button(
            btn_area,
            text="\u2630  Manage",
            command=self._app.open_symbol_manager,
            bootstyle="secondary-outline",  # type: ignore[arg-type]
            style="AutoRefresh.TButton",
        )
        self._manage_btn.pack(side=RIGHT, padx=(8, 0))

        self._auto_btn = ttk.Button(
            btn_area,
            text="\u21bb  Auto: OFF",
            command=self._app.toggle_auto_refresh,
            bootstyle="secondary-outline",  # type: ignore[arg-type]
            style="AutoRefresh.TButton",
        )
        self._auto_btn.pack(side=RIGHT, padx=(8, 0))

        self._refresh_btn = ttk.Button(
            btn_area,
            text="\u27f3  Refresh",
            command=self._app.refresh_quotes,
            bootstyle="info",  # type: ignore[arg-type]
            style="Refresh.TButton",
        )
        self._refresh_btn.pack(side=RIGHT)

        # Refresh interval selector
        interval_frame = ttk.Frame(btn_area, style="Header.TFrame")
        interval_frame.pack(side=RIGHT, padx=(0, 12))

        ttk.Label(interval_frame, text="Interval:", style="Intervallbl.TLabel").pack(
            side=LEFT, padx=(0, 4),
        )
        self._interval_var = tk.StringVar(value=f"{DEFAULT_REFRESH_INTERVAL}s")
        self._interval_combo = ttk.Combobox(
            interval_frame,
            textvariable=self._interval_var,
            values=[f"{v}s" for v in REFRESH_INTERVALS],
            width=4,
            state="readonly",
        )
        self._interval_combo.pack(side=LEFT)
        self._interval_combo.bind("<<ComboboxSelected>>", self._on_interval_change)

    def _on_interval_change(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._app.set_refresh_interval(int(self._interval_var.get().rstrip("s")))
        self.focus_set()

    # -- Public interface --

    def set_status_fetching(self) -> None:
        """Show fetching state with pulsing dot."""
        self._fetching = True
        self._pulse_dot()

    def _pulse_dot(self) -> None:
        """Animate the dot between accent and dim while fetching."""
        if not self._fetching:
            return
        current = self._dot_label.cget("foreground")
        next_clr = CLR_ACCENT if current != CLR_ACCENT else "#3d6a9e"
        self._dot_label.configure(
            text="  \u2022 Fetching\u2026", foreground=next_clr,
        )
        self._pulse_id = self.after(300, self._pulse_dot)

    def set_status_connected(self) -> None:
        """Show connected state on dot label."""
        self._stop_pulse()
        self._dot_label.configure(text="  \u2022 Connected", foreground=CLR_GREEN)

    def set_status_error(self) -> None:
        """Show error state on dot label."""
        self._stop_pulse()
        self._dot_label.configure(text="  \u2022 Error", foreground=CLR_RED)

    def _stop_pulse(self) -> None:
        """Cancel any running pulse animation."""
        self._fetching = False
        if self._pulse_id is not None:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None

    def set_updated_time(self, text: str) -> None:
        """Update the 'Last Updated' display."""
        self._updated_label.configure(text=text)

    def set_refresh_enabled(self, enabled: bool) -> None:
        """Enable/disable the refresh button."""
        self._refresh_btn.configure(state="normal" if enabled else "disabled")

    def set_auto_refresh_display(self, active: bool) -> None:
        """Update auto-refresh button appearance."""
        if active:
            self._auto_btn.configure(
                text="\u21bb  Auto: ON",
                bootstyle="success",  # type: ignore[arg-type]
            )
        else:
            self._auto_btn.configure(
                text="\u21bb  Auto: OFF",
                bootstyle="secondary-outline",  # type: ignore[arg-type]
            )

    def update_market_status(self) -> None:
        """Refresh the market status label and schedule the next update."""
        text, style = _get_market_status()
        self._market_status_label.configure(text=text, style=style)
        self.after(60_000, self.update_market_status)

    def set_market_info(self, info: str) -> None:
        """Display additional market info from the API."""
        self._market_status_label.configure(text=info)
