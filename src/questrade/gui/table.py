"""Quote treeview table with synchronized status column."""
from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, W, Y

from questrade.gui.formatting import (
    fmt_change,
    fmt_price,
    fmt_sparkline,
    fmt_status,
    fmt_time,
    fmt_volume,
    get_change_value,
    sort_key_for_column,
)
from questrade.gui.styles import (
    CLR_BG_CARD,
    CLR_BG_ROW_ALT,
    CLR_GREEN,
    CLR_ORANGE,
    CLR_RED,
    CLR_TEXT_BRIGHT,
    CLR_TEXT_DIM,
    FONT_FAMILY,
)
from questrade.models.quote import Quote

if TYPE_CHECKING:
    from questrade.gui.app import QuoteApp

COLUMNS = (
    "symbol", "last_price", "change", "bid", "ask",
    "spread", "high", "low", "volume", "last_trade", "trend",
)

HEADINGS: dict[str, str] = {
    "symbol": "SYMBOL",
    "last_price": "LAST PRICE",
    "change": "CHANGE",
    "bid": "BID",
    "ask": "ASK",
    "spread": "SPREAD",
    "high": "HIGH",
    "low": "LOW",
    "volume": "VOLUME",
    "last_trade": "LAST TRADE",
    "trend": "TREND",
    "status": "STATUS",
}

COL_CONFIG: dict[str, dict[str, object]] = {
    "symbol":     {"width": 90,  "minwidth": 70,  "anchor": W},
    "last_price": {"width": 100, "minwidth": 90,  "anchor": tk.E},
    "change":     {"width": 140, "minwidth": 110, "anchor": tk.E},
    "bid":        {"width": 80,  "minwidth": 60,  "anchor": tk.E},
    "ask":        {"width": 80,  "minwidth": 60,  "anchor": tk.E},
    "spread":     {"width": 110, "minwidth": 80,  "anchor": tk.E},
    "high":       {"width": 90,  "minwidth": 70,  "anchor": tk.E},
    "low":        {"width": 90,  "minwidth": 70,  "anchor": tk.E},
    "volume":     {"width": 80,  "minwidth": 60,  "anchor": tk.E},
    "last_trade": {"width": 160, "minwidth": 130, "anchor": tk.CENTER},
    "trend":      {"width": 140, "minwidth": 100, "anchor": tk.CENTER},
}

# Flash duration in ms
_FLASH_DURATION = 400


def _fmt_spread(quote: Quote) -> str:
    """Format bid/ask spread as '$0.45 (18bp)' or '---'."""
    if quote.bid_price is None or quote.ask_price is None:
        return "---"
    spread = quote.ask_price - quote.bid_price
    if quote.ask_price != 0:
        bps = spread / quote.ask_price * 10_000
        return f"${spread:.2f} ({bps:.0f}bp)"
    return f"${spread:.2f}"


class QuoteTable(ttk.Frame):
    """Dual treeview (quotes + status) with synchronized scrolling."""

    def __init__(self, parent: QuoteApp) -> None:
        super().__init__(parent, style="Dark.TFrame", padding=(16, 12, 16, 0))
        self._app = parent
        self._programmatic_select = False
        self._prev_prices: dict[str, float] = {}
        self._tooltip: _Tooltip | None = None
        self._build()

    def _build(self) -> None:
        self._tree = ttk.Treeview(
            self,
            columns=COLUMNS,
            show="headings",
            style="Custom.Treeview",
            selectmode="browse",
        )

        for col in COLUMNS:
            if col == "trend":
                self._tree.heading(col, text=HEADINGS[col])
            else:
                self._tree.heading(
                    col, text=HEADINGS[col],
                    command=lambda c=col: self._app.on_sort(c),
                )
            cfg = COL_CONFIG[col]
            self._tree.column(
                col, width=cfg["width"], minwidth=cfg["minwidth"],
                anchor=cfg["anchor"],
            )

        _alt = CLR_BG_ROW_ALT
        self._tree.tag_configure("halted", foreground=CLR_RED)
        self._tree.tag_configure("delayed", foreground=CLR_ORANGE)
        self._tree.tag_configure("stripe", background=_alt)
        self._tree.tag_configure("halted_stripe", foreground=CLR_RED, background=_alt)
        self._tree.tag_configure("delayed_stripe", foreground=CLR_ORANGE, background=_alt)
        self._tree.tag_configure("change_up", foreground=CLR_GREEN)
        self._tree.tag_configure("change_down", foreground=CLR_RED)
        self._tree.tag_configure("change_up_stripe", foreground=CLR_GREEN, background=_alt)
        self._tree.tag_configure("change_down_stripe", foreground=CLR_RED, background=_alt)
        # Flash tags (temporarily applied on price change)
        self._tree.tag_configure("flash_up", background="#2d4a2d")
        self._tree.tag_configure("flash_down", background="#4a2d2d")

        # Status treeview
        self._status_tree = ttk.Treeview(
            self,
            columns=("status",),
            show="headings",
            style="Custom.Treeview",
            selectmode="none",
        )
        self._status_tree.heading(
            "status", text="STATUS",
            command=lambda: self._app.on_sort("status"),
        )
        self._status_tree.column("status", width=100, minwidth=80, anchor=tk.CENTER)

        self._status_tree.tag_configure("realtime", foreground=CLR_TEXT_BRIGHT)
        self._status_tree.tag_configure(
            "realtime_stripe", foreground=CLR_TEXT_BRIGHT, background=_alt,
        )
        self._status_tree.tag_configure("halted", foreground=CLR_RED)
        self._status_tree.tag_configure("halted_stripe", foreground=CLR_RED, background=_alt)
        self._status_tree.tag_configure("delayed", foreground=CLR_ORANGE)
        self._status_tree.tag_configure(
            "delayed_stripe", foreground=CLR_ORANGE, background=_alt,
        )

        # Synchronized scrollbar
        def _sync_scroll(*args: str) -> None:
            self._tree.yview(*args)
            self._status_tree.yview(*args)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=_sync_scroll)

        def _on_main_scroll(*args: str) -> None:
            scrollbar.set(*args)
            self._status_tree.yview("moveto", args[0])

        def _on_status_scroll(*args: str) -> None:
            scrollbar.set(*args)
            self._tree.yview("moveto", args[0])

        self._tree.configure(yscrollcommand=_on_main_scroll)
        self._status_tree.configure(yscrollcommand=_on_status_scroll)

        def _on_mousewheel(event: tk.Event) -> str:  # type: ignore[type-arg]
            delta = -1 * (event.delta // 120)
            self._tree.yview_scroll(delta, "units")
            self._status_tree.yview_scroll(delta, "units")
            return "break"

        self._tree.bind("<MouseWheel>", _on_mousewheel)
        self._status_tree.bind("<MouseWheel>", _on_mousewheel)

        scrollbar.pack(side=RIGHT, fill=Y)
        self._status_tree.pack(side=RIGHT, fill=Y)
        self._tree.pack(side=LEFT, fill=BOTH, expand=True)

        # Row selection bindings
        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self._status_tree.bind("<Button-1>", self._on_status_tree_click)

        # Tooltip on hover for sparkline/trend column
        self._tree.bind("<Motion>", self._on_motion)
        self._tree.bind("<Leave>", self._on_leave)

    # -- Display --

    def populate(
        self,
        quotes: list[Quote],
        sort_column: str,
        sort_descending: bool,
        price_history: dict[str, list[float]],
        selected_symbol: str | None,
    ) -> None:
        """Sort and display quotes in both treeviews."""
        self._programmatic_select = True

        # Detect price changes for flash animation
        flash_map: dict[str, str] = {}
        for q in quotes:
            if q.last_trade_price is not None and q.symbol in self._prev_prices:
                prev = self._prev_prices[q.symbol]
                if q.last_trade_price > prev:
                    flash_map[q.symbol] = "flash_up"
                elif q.last_trade_price < prev:
                    flash_map[q.symbol] = "flash_down"

        # Update previous prices
        for q in quotes:
            if q.last_trade_price is not None:
                self._prev_prices[q.symbol] = q.last_trade_price

        sorted_quotes = sorted(
            quotes,
            key=lambda q: sort_key_for_column(q, sort_column),
            reverse=sort_descending,
        )

        for item in self._tree.get_children():
            self._tree.delete(item)
        for item in self._status_tree.get_children():
            self._status_tree.delete(item)

        for i, quote in enumerate(sorted_quotes):
            is_stripe = i % 2 == 1
            tags: list[str] = []
            status_tags: list[str] = []

            if quote.is_halted:
                tags = ["halted_stripe" if is_stripe else "halted"]
                status_tags = ["halted_stripe" if is_stripe else "halted"]
            elif quote.delay > 0:
                tags = ["delayed_stripe" if is_stripe else "delayed"]
                status_tags = ["delayed_stripe" if is_stripe else "delayed"]
            else:
                change = get_change_value(quote)
                if change is not None and change > 0:
                    tags = ["change_up_stripe" if is_stripe else "change_up"]
                elif change is not None and change < 0:
                    tags = ["change_down_stripe" if is_stripe else "change_down"]
                elif is_stripe:
                    tags = ["stripe"]
                status_tags = ["realtime_stripe" if is_stripe else "realtime"]

            # Add flash tag if price changed
            if quote.symbol in flash_map:
                tags.append(flash_map[quote.symbol])

            iid = self._tree.insert("", END, values=(
                f"  {quote.symbol}",
                fmt_price(quote.last_trade_price),
                fmt_change(quote),
                fmt_price(quote.bid_price),
                fmt_price(quote.ask_price),
                _fmt_spread(quote),
                fmt_price(quote.high_price),
                fmt_price(quote.low_price),
                fmt_volume(quote.volume),
                fmt_time(quote.last_trade_time),
                fmt_sparkline(price_history.get(quote.symbol, [])),
            ), tags=tuple(tags) if tags else ())

            self._status_tree.insert("", END, values=(
                fmt_status(quote),
            ), tags=tuple(status_tags))

            # Schedule flash removal
            if quote.symbol in flash_map:
                flash_tag = flash_map[quote.symbol]
                base_tags = [t for t in tags if t != flash_tag]
                self.after(
                    _FLASH_DURATION,
                    self._remove_flash, iid, tuple(base_tags),
                )

        self._update_heading_text(sort_column, sort_descending)

        # Re-select previously selected row
        if selected_symbol:
            for item in self._tree.get_children():
                vals = self._tree.item(item, "values")
                if vals and vals[0].strip() == selected_symbol:
                    self._tree.selection_set(item)
                    self._app.show_detail_for(selected_symbol)
                    break

        self.after_idle(self._reset_programmatic_select)

    def _remove_flash(self, iid: str, base_tags: tuple[str, ...]) -> None:
        """Remove flash tag from a row, restoring base tags."""
        if self._tree.exists(iid):
            self._tree.item(iid, tags=base_tags)

    def _update_heading_text(self, sort_column: str, sort_descending: bool) -> None:
        """Update column headings to show sort indicator."""
        arrow = " \u25b2" if not sort_descending else " \u25bc"
        for col in COLUMNS:
            text = HEADINGS[col]
            if col == sort_column and col != "trend":
                text += arrow
            self._tree.heading(col, text=text)

        status_text = HEADINGS["status"]
        if sort_column == "status":
            status_text += arrow
        self._status_tree.heading("status", text=status_text)

    # -- Sparkline Tooltip --

    def _on_motion(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Show tooltip when hovering over the trend column."""
        col_id = self._tree.identify_column(event.x)
        row_id = self._tree.identify_row(event.y)
        # trend is the last column
        col_index = COLUMNS.index("trend") + 1  # 1-based
        if col_id != f"#{col_index}" or not row_id:
            self._hide_tooltip()
            return

        vals = self._tree.item(row_id, "values")
        if not vals:
            self._hide_tooltip()
            return
        symbol = vals[0].strip()
        history = self._app.get_price_history(symbol)
        if len(history) < 2:
            self._hide_tooltip()
            return

        # Build tooltip text
        lines = [f"{symbol} Price History ({len(history)} ticks)"]
        lines.append(f"Min: {fmt_price(min(history))}")
        lines.append(f"Max: {fmt_price(max(history))}")
        lines.append(f"Avg: {fmt_price(sum(history) / len(history))}")
        lines.append("")
        lines.append(
            "  ".join(f"${p:,.2f}" for p in history[-10:]),
        )
        if len(history) > 10:
            lines[-1] = f"...{len(history) - 10} more  " + lines[-1]

        text = "\n".join(lines)
        x = self._tree.winfo_rootx() + event.x + 15
        y = self._tree.winfo_rooty() + event.y + 10

        if self._tooltip is None:
            self._tooltip = _Tooltip(self._tree, text, x, y)
        else:
            self._tooltip.update_content(text, x, y)

    def _on_leave(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._hide_tooltip()

    def _hide_tooltip(self) -> None:
        if self._tooltip is not None:
            self._tooltip.destroy()
            self._tooltip = None

    # -- Selection --

    def _reset_programmatic_select(self) -> None:
        self._programmatic_select = False

    def _on_row_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._programmatic_select:
            return
        selection = self._tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self._tree.item(item, "values")
        if not values:
            return
        symbol = values[0].strip()

        # Sync status tree selection
        main_items = self._tree.get_children()
        status_items = self._status_tree.get_children()
        try:
            idx = list(main_items).index(item)
            if idx < len(status_items):
                self._status_tree.selection_set(status_items[idx])
        except ValueError:
            pass

        self._app.on_row_selected(symbol)

    def _on_status_tree_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        row_id = self._status_tree.identify_row(event.y)
        if not row_id:
            return
        status_items = list(self._status_tree.get_children())
        main_items = list(self._tree.get_children())
        try:
            idx = status_items.index(row_id)
        except ValueError:
            return
        if 0 <= idx < len(main_items):
            self._tree.selection_set(main_items[idx])
            self._tree.event_generate("<<TreeviewSelect>>")

    def clear_selection(self) -> None:
        """Remove all row selections."""
        self._tree.selection_remove(*self._tree.selection())


class _Tooltip:
    """Lightweight tooltip window for treeview cells."""

    def __init__(self, parent: tk.Widget, text: str, x: int, y: int) -> None:
        self._tw = tk.Toplevel(parent)
        self._tw.wm_overrideredirect(True)
        self._tw.wm_geometry(f"+{x}+{y}")
        self._tw.configure(background=CLR_BG_CARD)
        self._label = tk.Label(
            self._tw,
            text=text,
            justify=tk.LEFT,
            background=CLR_BG_CARD,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
            padx=8,
            pady=6,
        )
        self._label.pack()

    def update_content(self, text: str, x: int, y: int) -> None:
        """Update the tooltip text and position."""
        self._label.configure(text=text)
        self._tw.wm_geometry(f"+{x}+{y}")

    def destroy(self) -> None:
        """Remove the tooltip window."""
        self._tw.destroy()
