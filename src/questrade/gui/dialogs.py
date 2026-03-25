"""Dialog windows (Symbol Manager, etc.)."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, W, X, Y

from questrade.gui.styles import (
    CLR_BG_CARD,
    CLR_BG_DARK,
    CLR_BORDER,
    CLR_TEXT,
    FONT_FAMILY,
)

if TYPE_CHECKING:
    from questrade.gui.app import QuoteApp


def open_symbol_manager(app: QuoteApp) -> None:
    """Open the symbol management dialog."""
    from questrade.config import TARGET_SYMBOLS, reload_symbols, save_symbols
    from questrade.models.symbol import SymbolConfig

    dlg = tk.Toplevel(app)
    dlg.title("Manage Symbols")
    dlg.geometry("900x620")
    dlg.configure(background=CLR_BG_CARD)
    dlg.transient(app)
    dlg.grab_set()

    # Header
    hdr = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 12))
    hdr.pack(fill=X)
    ttk.Label(hdr, text="Manage Watchlist", style="DlgHd.TLabel").pack(anchor=W)
    count_lbl = ttk.Label(
        hdr, text=f"{len(TARGET_SYMBOLS)} symbols", style="DlgDim.TLabel",
    )
    count_lbl.pack(anchor=W)

    # Scrollable symbol list
    list_frame = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 8))
    list_frame.pack(fill=BOTH, expand=True)

    canvas = tk.Canvas(list_frame, background=CLR_BG_CARD, highlightthickness=0)
    list_scrollbar = ttk.Scrollbar(
        list_frame, orient="vertical", command=canvas.yview,
    )
    inner = ttk.Frame(canvas, style="Dlg.TFrame")

    inner.bind(
        "<Configure>",
        lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    inner_window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=list_scrollbar.set)

    # Keep inner frame width in sync with canvas so rows stretch fully
    def _on_canvas_resize(event: tk.Event) -> None:  # type: ignore[type-arg]
        canvas.itemconfigure(inner_window_id, width=event.width)

    canvas.bind("<Configure>", _on_canvas_resize)

    list_scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)

    current_symbols: list[SymbolConfig] = list(TARGET_SYMBOLS)
    original_symbols: list[SymbolConfig] = list(TARGET_SYMBOLS)

    def _has_changes() -> bool:
        if len(current_symbols) != len(original_symbols):
            return True
        return any(
            a.symbol != b.symbol or a.exchange != b.exchange or a.name != b.name
            for a, b in zip(current_symbols, original_symbols, strict=True)
        )

    def _rebuild_list() -> None:
        for w in inner.winfo_children():
            w.destroy()
        for i, sym in enumerate(current_symbols):
            row = ttk.Frame(inner, style="Dlg.TFrame")
            row.pack(fill=X, pady=2)
            # Pack delete button first so it always has space
            ttk.Button(
                row, text="\u2715", width=3,
                bootstyle="danger-outline",  # type: ignore[arg-type]
                command=lambda idx=i: _remove(idx),
            ).pack(side=RIGHT, padx=(0, 8))
            ttk.Label(
                row, text=f"{sym.symbol}  ({sym.exchange})",
                style="DlgLbl.TLabel", width=20,
            ).pack(side=LEFT)
            ttk.Label(
                row, text=sym.name, style="DlgDim.TLabel",
            ).pack(side=LEFT, padx=(8, 0), fill=X, expand=True)
        count_lbl.configure(text=f"{len(current_symbols)} symbols")

    def _remove(idx: int) -> None:
        current_symbols.pop(idx)
        _rebuild_list()

    _rebuild_list()

    # Bottom buttons (pack early with side=BOTTOM so they're always visible)
    btn_row = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 0, 16, 12))
    btn_row.pack(side=tk.BOTTOM, fill=X)

    def _save() -> None:
        save_symbols(current_symbols)
        reload_symbols()
        app.on_symbols_saved(current_symbols)
        dlg.destroy()

    def _on_close() -> None:
        if not _has_changes():
            dlg.destroy()
            return
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Save before closing?",
            parent=dlg,
        )
        if result is True:
            _save()
        elif result is False:
            dlg.destroy()
        # result is None → Cancel, do nothing

    dlg.protocol("WM_DELETE_WINDOW", _on_close)

    ttk.Button(
        btn_row, text="Save", bootstyle="success",  # type: ignore[arg-type]
        command=_save,
    ).pack(side=RIGHT, padx=(4, 0))
    ttk.Button(
        btn_row, text="Cancel",
        bootstyle="secondary-outline",  # type: ignore[arg-type]
        command=_on_close,
    ).pack(side=RIGHT)

    # --- Add symbol area with autocomplete ---
    add_frame = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 8, 16, 12))
    add_frame.pack(fill=X)

    tk.Frame(add_frame, background=CLR_BORDER, height=1).pack(fill=X, pady=(0, 8))

    ttk.Label(
        add_frame, text="Search and add symbol:", style="DlgDim.TLabel",
    ).pack(anchor=W, pady=(0, 4))

    search_row = ttk.Frame(add_frame, style="Dlg.TFrame")
    search_row.pack(fill=X)

    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_row, textvariable=search_var, width=20)
    search_entry.pack(side=LEFT, padx=(0, 4))

    # Results listbox
    results_frame = ttk.Frame(add_frame, style="Dlg.TFrame")
    results_frame.pack(fill=X, pady=(4, 0))

    results_listbox = tk.Listbox(
        results_frame,
        height=8,
        background=CLR_BG_DARK,
        foreground=CLR_TEXT,
        selectbackground="#3e4451",
        selectforeground=CLR_TEXT,
        font=(FONT_FAMILY, 9),
        highlightthickness=0,
        borderwidth=1,
        relief="flat",
    )
    results_listbox.pack(fill=X)

    # Status label for search
    search_status = ttk.Label(
        add_frame, text="Type to search...", style="DlgDim.TLabel",
    )
    search_status.pack(anchor=W, pady=(2, 0))

    # Store search results for selection
    search_results: list[object] = []
    search_timer_id: list[str | None] = [None]

    def _on_search_changed(*_args: object) -> None:
        """Debounce search - fire 300ms after last keystroke."""
        if search_timer_id[0] is not None:
            dlg.after_cancel(search_timer_id[0])
        prefix = search_var.get().strip()
        if len(prefix) < 2:
            results_listbox.delete(0, tk.END)
            search_results.clear()
            search_status.configure(text="Type at least 2 characters...")
            return
        search_timer_id[0] = dlg.after(300, lambda: _do_search(prefix))

    def _do_search(prefix: str) -> None:
        """Run search in background thread."""
        search_status.configure(text="Searching...")
        threading.Thread(
            target=_search_worker, args=(prefix,), daemon=True,
        ).start()

    def _search_worker(prefix: str) -> None:
        """Background API call for symbol search."""
        try:
            from questrade.api.auth import get_initial_tokens
            from questrade.api.client import build_client
            from questrade.api.symbols import search_symbols

            tokens = get_initial_tokens()
            client = build_client(tokens.access_token, tokens.api_server)
            results = search_symbols(prefix, client)
            dlg.after(0, _on_search_results, results)
        except Exception as exc:  # noqa: BLE001
            dlg.after(0, _on_search_error, str(exc))

    def _on_search_results(results: list[object]) -> None:
        from questrade.models.symbol import SymbolSearchResult

        results_listbox.delete(0, tk.END)
        search_results.clear()
        search_results.extend(results)
        for r in results:
            if isinstance(r, SymbolSearchResult):
                results_listbox.insert(
                    tk.END,
                    f"{r.symbol}  ({r.listing_exchange})  —  {r.description}",
                )
        count = len(results)
        search_status.configure(
            text=f"{count} result{'s' if count != 1 else ''} found",
        )

    def _on_search_error(msg: str) -> None:
        search_status.configure(text=f"Search error: {msg}")

    search_var.trace_add("write", _on_search_changed)

    def _add_selected() -> None:
        from questrade.models.symbol import SymbolSearchResult

        sel = results_listbox.curselection()
        if not sel or not search_results:
            return
        idx = sel[0]
        if idx >= len(search_results):
            return
        result = search_results[idx]
        if not isinstance(result, SymbolSearchResult):
            return
        # Check for duplicates
        if any(
            c.symbol == result.symbol
            and c.exchange == result.listing_exchange
            for c in current_symbols
        ):
            return
        current_symbols.append(SymbolConfig(
            symbol=result.symbol,
            exchange=result.listing_exchange,
            name=result.description,
        ))
        _rebuild_list()
        search_var.set("")
        results_listbox.delete(0, tk.END)
        search_results.clear()

    ttk.Button(
        search_row, text="Add Selected",
        bootstyle="success",  # type: ignore[arg-type]
        command=_add_selected,
    ).pack(side=LEFT, padx=(4, 0))

    # Also allow double-click to add
    results_listbox.bind("<Double-Button-1>", lambda _e: _add_selected())

    # Bind Enter key on results listbox to add selected
    results_listbox.bind("<Return>", lambda _e: _add_selected())

    # --- Manual add fallback ---
    manual_sep = tk.Frame(add_frame, background=CLR_BORDER, height=1)
    manual_sep.pack(fill=X, pady=(8, 4))

    ttk.Label(
        add_frame, text="Or add manually:", style="DlgDim.TLabel",
    ).pack(anchor=W, pady=(0, 4))

    manual_row = ttk.Frame(add_frame, style="Dlg.TFrame")
    manual_row.pack(fill=X)

    sym_var = tk.StringVar()
    ttk.Entry(manual_row, textvariable=sym_var, width=10).pack(
        side=LEFT, padx=(0, 4),
    )

    exchanges = ["NASDAQ", "NYSE", "TSX", "TSX-V", "ARCA"]
    exch_var = tk.StringVar(value="NASDAQ")
    ttk.Combobox(
        manual_row, textvariable=exch_var, values=exchanges,
        width=8, state="readonly",
    ).pack(side=LEFT, padx=(0, 4))

    name_var = tk.StringVar()
    ttk.Entry(manual_row, textvariable=name_var, width=20).pack(
        side=LEFT, padx=(0, 4),
    )

    def _add_manual() -> None:
        s = sym_var.get().strip().upper()
        if not s:
            return
        if any(
            c.symbol == s and c.exchange == exch_var.get()
            for c in current_symbols
        ):
            return
        n = name_var.get().strip() or s
        current_symbols.append(
            SymbolConfig(symbol=s, exchange=exch_var.get(), name=n),
        )
        sym_var.set("")
        name_var.set("")
        _rebuild_list()

    ttk.Button(
        manual_row, text="Add",
        bootstyle="success",  # type: ignore[arg-type]
        command=_add_manual,
    ).pack(side=LEFT)
