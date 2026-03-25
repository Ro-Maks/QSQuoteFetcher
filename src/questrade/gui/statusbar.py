"""Status bar at the bottom of the application window."""
from __future__ import annotations

import ttkbootstrap as ttk
from ttkbootstrap.constants import LEFT, RIGHT

_SPINNER_FRAMES = ("◐", "◓", "◑", "◒")


class StatusBar(ttk.Frame):
    """Bottom status bar showing timestamps, status, and countdown."""

    def __init__(self, parent: ttk.Window) -> None:
        super().__init__(parent, style="Dark.TFrame", padding=(20, 8, 20, 12))
        self._spinner_idx = 0
        self._spinner_timer_id: str | None = None
        self._build()

    def _build(self) -> None:
        self._time_label = ttk.Label(self, text="", style="StatusBar.TLabel")
        self._time_label.pack(side=LEFT)

        self._status_label = ttk.Label(self, text="", style="StatusBar.TLabel")
        self._status_label.pack(side=RIGHT)

        self._spinner_label = ttk.Label(self, text="", style="Countdown.TLabel")
        self._spinner_label.pack(side=RIGHT, padx=(0, 4))

        self._countdown_label = ttk.Label(self, text="", style="Countdown.TLabel")
        self._countdown_label.pack(side=RIGHT, padx=(0, 8))

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

    def start_spinner(self) -> None:
        """Start the animated spinner."""
        if self._spinner_timer_id is not None:
            return
        self._spinner_idx = 0
        self._tick_spinner()

    def stop_spinner(self) -> None:
        """Stop the spinner and clear the label."""
        if self._spinner_timer_id is not None:
            self.after_cancel(self._spinner_timer_id)
            self._spinner_timer_id = None
        self._spinner_label.configure(text="")

    def _tick_spinner(self) -> None:
        self._spinner_label.configure(text=_SPINNER_FRAMES[self._spinner_idx])
        self._spinner_idx = (self._spinner_idx + 1) % len(_SPINNER_FRAMES)
        self._spinner_timer_id = self.after(250, self._tick_spinner)
