"""Color palette, font constants, and ttk style configuration."""
from __future__ import annotations

import ttkbootstrap as ttk

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

REFRESH_INTERVALS = [5, 10, 15, 30, 60]
DEFAULT_REFRESH_INTERVAL = 10


def configure_styles() -> None:
    """Configure all ttk styles for the application."""
    style = ttk.Style()

    style.configure("Header.TFrame", background=CLR_BG_HEADER)
    style.configure("Card.TFrame", background=CLR_BG_CARD)
    style.configure("Dark.TFrame", background=CLR_BG_DARK)

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
        "Mko.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_GREEN,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "Mkc.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_TEXT_DIM,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "Mkx.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_ORANGE,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "StatusDot.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_GREEN,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "Refreshlbl.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_TEXT_DIM,
        font=(FONT_FAMILY, 9),
    )
    style.configure(
        "Refreshval.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_TEXT,
        font=(FONT_FAMILY, 9),
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
    style.configure(
        "Intervallbl.TLabel",
        background=CLR_BG_HEADER,
        foreground=CLR_TEXT_DIM,
        font=(FONT_FAMILY, 9),
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

    # Detail panel
    style.configure("Dtl.TFrame", background=CLR_BG_CARD)
    style.configure(
        "DtlHd.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT_BRIGHT,
        font=(FONT_FAMILY, 13, "bold"),
    )
    style.configure(
        "DtlK.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT_DIM,
        font=(FONT_FAMILY, 9),
    )
    style.configure(
        "DtlV.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "DtlHlt.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_RED,
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.configure(
        "DtlGrn.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_GREEN,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "DtlRng.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT_DIM,
        font=(FONT_FAMILY, 9),
    )
    style.configure(
        "DtlSpk.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_ACCENT,
        font=(FONT_FAMILY, 14),
    )

    # Dialog styles
    style.configure("Dlg.TFrame", background=CLR_BG_CARD)
    style.configure(
        "DlgHd.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT_BRIGHT,
        font=(FONT_FAMILY, 13, "bold"),
    )
    style.configure(
        "DlgLbl.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT,
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "DlgDim.TLabel",
        background=CLR_BG_CARD,
        foreground=CLR_TEXT_DIM,
        font=(FONT_FAMILY, 9),
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
