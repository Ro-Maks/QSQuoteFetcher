"""Status bar at the bottom of the application window."""
from __future__ import annotations

import ttkbootstrap as ttk
from ttkbootstrap.constants import LEFT, RIGHT


class StatusBar(ttk.Frame):
    """Bottom status bar showing timestamps, status, and countdown."""

    def __init__(self, parent: ttk.Window) -> None:
        super().__init__(parent, style="Dark.TFrame", padding=(20, 8, 20, 12))
        self._build()

    def _build(self) -> None:
        self._time_label = ttk.Label(self, text="", style="StatusBar.TLabel")
        self._time_label.pack(side=LEFT)

        self._status_label = ttk.Label(self, text="", style="StatusBar.TLabel")
        self._status_label.pack(side=RIGHT)

        self._countdown_label = ttk.Label(self, text="", style="Countdown.TLabel")
        self._countdown_label.pack(side=RIGHT, padx=(0, 16))

    # -- Public interface --

    def set_time_text(self, text: str) -> None:
        """Update the left-side timestamp display."""
        self._time_label.configure(text=text)

    def set_status(self, text: str, style: str = "StatusBar.TLabel") -> None:
        """Update the right-side status display."""
        self._status_label.configure(text=text, style=style)

    def set_countdown(self, text: str) -> None:
        """Update the countdown label."""
        self._countdown_label.configure(text=text)
