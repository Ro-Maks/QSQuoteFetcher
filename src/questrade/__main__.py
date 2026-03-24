"""Entry point for ``python -m questrade``."""
from __future__ import annotations

import sys


def _entry() -> None:
    if "--gui" in sys.argv:
        from questrade.gui import main as gui_main
        gui_main()
    else:
        from questrade.main import main as cli_main
        cli_main()


_entry()
