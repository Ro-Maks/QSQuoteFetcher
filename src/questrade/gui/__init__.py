"""GUI package for the Questrade Quote Fetcher."""
from __future__ import annotations


def main() -> None:
    """Launch the GUI application."""
    from questrade.gui.app import QuoteApp

    app = QuoteApp()
    app.mainloop()
