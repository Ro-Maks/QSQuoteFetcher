"""Expandable tabbed detail panel showing metrics and charts."""
from __future__ import annotations

import threading
import tkinter as tk
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import ttkbootstrap as ttk
from ttkbootstrap.constants import E, W, X

from questrade.gui.formatting import fmt_price, fmt_sparkline, fmt_time
from questrade.gui.styles import (
    CLR_ACCENT,
    CLR_BG_DARK,
    CLR_BORDER,
    CLR_GREEN,
    CLR_RED,
    CLR_TEXT_BRIGHT,
    CLR_TEXT_DIM,
    FONT_FAMILY,
)
from questrade.models.quote import Quote

if TYPE_CHECKING:
    from questrade.gui.app import QuoteApp


class DetailPanel(ttk.Frame):
    """Expandable tabbed panel showing detailed metrics and charts."""

    def __init__(self, parent: QuoteApp) -> None:
        super().__init__(parent, style="Dark.TFrame", padding=(16, 0, 16, 0))
        self._app = parent
        self._fields: dict[str, ttk.Label | tk.Canvas] = {}
        self._candle_cache: dict[str, list[object]] = {}
        self._current_symbol_id: int | None = None
        self._current_interval: str = "FiveMinutes"
        self._build()

    def _build(self) -> None:
        accent = tk.Frame(self, background=CLR_ACCENT, height=2)
        accent.pack(fill=X)

        # Notebook (tabs)
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=X)

        # Tab 1: Overview
        self._overview_frame = ttk.Frame(self._notebook, style="Dtl.TFrame", padding=(20, 12))
        self._notebook.add(self._overview_frame, text="  Overview  ")
        self._build_overview(self._overview_frame)

        # Tab 2: Chart
        self._chart_frame = ttk.Frame(self._notebook, style="Dtl.TFrame", padding=(20, 12))
        self._notebook.add(self._chart_frame, text="  Chart  ")
        self._build_chart(self._chart_frame)

    def _build_overview(self, parent: ttk.Frame) -> None:
        """Build the overview metrics tab."""
        # Row 0: Header
        hdr_frame = ttk.Frame(parent, style="Dtl.TFrame")
        hdr_frame.grid(row=0, column=0, columnspan=8, sticky="ew", pady=(0, 8))
        hdr_frame.columnconfigure(0, weight=1)
        self._symbol_lbl = ttk.Label(hdr_frame, text="", style="DtlHd.TLabel")
        self._symbol_lbl.grid(row=0, column=0, sticky=W)
        sts_lbl = ttk.Label(hdr_frame, text="", style="DtlV.TLabel")
        sts_lbl.grid(row=0, column=1, sticky=E)
        self._fields["sts"] = sts_lbl

        # Row 1: Day range bar
        range_frame = ttk.Frame(parent, style="Dtl.TFrame")
        range_frame.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(0, 8))
        ttk.Label(
            range_frame, text="Day Range", style="DtlK.TLabel",
        ).pack(side=tk.LEFT, padx=(0, 8))
        range_lo_lbl = ttk.Label(range_frame, text="---", style="DtlRng.TLabel")
        range_lo_lbl.pack(side=tk.LEFT, padx=(0, 4))
        self._fields["range_lo"] = range_lo_lbl
        range_canvas = tk.Canvas(
            range_frame, height=14, width=300,
            background=CLR_BG_DARK, highlightthickness=0,
        )
        range_canvas.pack(side=tk.LEFT, padx=4, fill=X, expand=True)
        self._fields["range_canvas"] = range_canvas
        range_hi_lbl = ttk.Label(range_frame, text="---", style="DtlRng.TLabel")
        range_hi_lbl.pack(side=tk.LEFT, padx=(4, 0))
        self._fields["range_hi"] = range_hi_lbl

        # Row 2: Key metrics
        metrics = [
            ("Open", "open"),
            ("VWAP", "vwap"),
            ("Spread", "spread"),
            ("Bid \u00d7 Size", "bid_depth"),
            ("Ask \u00d7 Size", "ask_depth"),
            ("Last Trade", "last_trade"),
        ]
        for col_idx, (label_text, key) in enumerate(metrics):
            ttk.Label(parent, text=label_text, style="DtlK.TLabel").grid(
                row=2, column=col_idx, sticky=W, padx=(0, 4),
            )
            val_lbl = ttk.Label(parent, text="---", style="DtlV.TLabel")
            val_lbl.grid(row=3, column=col_idx, sticky=W, padx=(0, 20))
            self._fields[key] = val_lbl

        # Row 4: Computed stats + sparkline
        stats_frame = ttk.Frame(parent, style="Dtl.TFrame")
        stats_frame.grid(row=4, column=0, columnspan=8, sticky="ew", pady=(8, 0))
        from_open_lbl = ttk.Label(stats_frame, text="", style="DtlV.TLabel")
        from_open_lbl.pack(side=tk.LEFT, padx=(0, 20))
        self._fields["from_open"] = from_open_lbl
        off_high_lbl = ttk.Label(stats_frame, text="", style="DtlV.TLabel")
        off_high_lbl.pack(side=tk.LEFT, padx=(0, 20))
        self._fields["off_high"] = off_high_lbl
        spark_lbl = ttk.Label(stats_frame, text="", style="DtlSpk.TLabel")
        spark_lbl.pack(side=tk.LEFT, padx=(0, 8))
        self._fields["sparkline"] = spark_lbl
        spark_stats_lbl = ttk.Label(stats_frame, text="", style="DtlK.TLabel")
        spark_stats_lbl.pack(side=tk.LEFT)
        self._fields["spark_stats"] = spark_stats_lbl

    def _build_chart(self, parent: ttk.Frame) -> None:
        """Build the candlestick chart tab."""
        # Period selector buttons
        btn_frame = ttk.Frame(parent, style="Dtl.TFrame")
        btn_frame.pack(fill=X, pady=(0, 8))

        self._chart_symbol_lbl = ttk.Label(
            btn_frame, text="", style="DtlHd.TLabel",
        )
        self._chart_symbol_lbl.pack(side=tk.LEFT, padx=(0, 16))

        for label, interval, days in [
            ("1D", "FiveMinutes", 1),
            ("5D", "FifteenMinutes", 5),
            ("1M", "OneDay", 30),
        ]:
            ttk.Button(
                btn_frame, text=label,
                bootstyle="info-outline",  # type: ignore[arg-type]
                command=lambda iv=interval, d=days: self._load_chart(iv, d),
                width=4,
            ).pack(side=tk.LEFT, padx=(0, 4))

        self._chart_status = ttk.Label(
            btn_frame, text="", style="DtlK.TLabel",
        )
        self._chart_status.pack(side=tk.LEFT, padx=(8, 0))

        # Canvas for drawing candles
        self._chart_canvas = tk.Canvas(
            parent, height=180, background=CLR_BG_DARK,
            highlightthickness=0,
        )
        self._chart_canvas.pack(fill=X, expand=True)

    # -- Public interface --

    def show(
        self, quote: Quote, name: str, price_history: list[float],
        after_widget: tk.Widget,
    ) -> None:
        """Populate and display the detail panel for the given quote."""
        cur = quote.last_trade_price
        lo, hi = quote.low_price, quote.high_price

        # Overview header
        self._symbol_lbl.configure(text=f"{quote.symbol}  \u2014  {name}")
        self._chart_symbol_lbl.configure(text=quote.symbol)
        self._current_symbol_id = quote.symbol_id

        # Status badge
        if quote.is_halted:
            self._fields["sts"].configure(
                text="\u26d4 HALTED", style="DtlHlt.TLabel",
            )
        elif quote.delay > 0:
            self._fields["sts"].configure(
                text=f"\u23f1 Delayed {quote.delay}m", style="DtlV.TLabel",
            )
        else:
            self._fields["sts"].configure(
                text="\u26a1 Real-Time", style="DtlGrn.TLabel",
            )

        # Day range bar
        if lo is not None and hi is not None and cur is not None:
            self._fields["range_lo"].configure(text=fmt_price(lo))
            self._fields["range_hi"].configure(text=fmt_price(hi))
            self.pack(fill=X, after=after_widget)
            self.update_idletasks()
            self._draw_range_bar(
                self._fields["range_canvas"], lo, hi, cur,  # type: ignore[arg-type]
            )
        else:
            self._fields["range_lo"].configure(text="---")
            self._fields["range_hi"].configure(text="---")
            canvas = self._fields["range_canvas"]
            canvas.delete("all")  # type: ignore[union-attr]

        # Key metrics
        self._fields["open"].configure(text=fmt_price(quote.open_price))
        self._fields["vwap"].configure(text=fmt_price(quote.vwap))

        if quote.bid_price is not None and quote.ask_price is not None:
            spread = quote.ask_price - quote.bid_price
            spread_pct = (spread / quote.ask_price * 100) if quote.ask_price else 0
            self._fields["spread"].configure(
                text=f"${spread:.2f} ({spread_pct:.2f}%)",
            )
        else:
            self._fields["spread"].configure(text="---")

        if quote.bid_price is not None:
            bid_txt = fmt_price(quote.bid_price)
            if quote.bid_size is not None:
                bid_txt += f" \u00d7 {quote.bid_size:,}"
            self._fields["bid_depth"].configure(text=bid_txt)
        else:
            self._fields["bid_depth"].configure(text="---")

        if quote.ask_price is not None:
            ask_txt = fmt_price(quote.ask_price)
            if quote.ask_size is not None:
                ask_txt += f" \u00d7 {quote.ask_size:,}"
            self._fields["ask_depth"].configure(text=ask_txt)
        else:
            self._fields["ask_depth"].configure(text="---")

        time_str = fmt_time(quote.last_trade_time)
        if quote.last_trade_size is not None:
            self._fields["last_trade"].configure(
                text=f"{quote.last_trade_size:,} @ {time_str}",
            )
        else:
            self._fields["last_trade"].configure(text=time_str)

        # From Open %
        if (
            cur is not None
            and quote.open_price is not None
            and quote.open_price != 0
        ):
            from_open_pct = (cur - quote.open_price) / quote.open_price * 100
            sign = "+" if from_open_pct >= 0 else ""
            style = "DtlGrn.TLabel" if from_open_pct >= 0 else "DtlHlt.TLabel"
            self._fields["from_open"].configure(
                text=f"From Open  {sign}{from_open_pct:.2f}%", style=style,
            )
        else:
            self._fields["from_open"].configure(
                text="From Open  ---", style="DtlV.TLabel",
            )

        # Off High %
        if cur is not None and hi is not None and hi != 0:
            off_high_pct = (cur - hi) / hi * 100
            style = "DtlGrn.TLabel" if off_high_pct >= 0 else "DtlHlt.TLabel"
            self._fields["off_high"].configure(
                text=f"Off High  {off_high_pct:.2f}%", style=style,
            )
        else:
            self._fields["off_high"].configure(
                text="Off High  ---", style="DtlV.TLabel",
            )

        # Sparkline
        if len(price_history) >= 2:
            self._fields["sparkline"].configure(text=fmt_sparkline(price_history))
            avg = sum(price_history) / len(price_history)
            mn = fmt_price(min(price_history))
            mx = fmt_price(max(price_history))
            ticks = len(price_history)
            self._fields["spark_stats"].configure(
                text=f"  Min {mn}  Avg {fmt_price(avg)}  Max {mx}  ({ticks} ticks)",
            )
        else:
            self._fields["sparkline"].configure(text="")
            self._fields["spark_stats"].configure(
                text="  Sparkline available after 2+ refreshes",
            )

        self.pack(fill=X, after=after_widget)

    def hide(self) -> None:
        """Hide the detail panel."""
        self.pack_forget()

    # -- Chart --

    def _load_chart(self, interval: str, days: int) -> None:
        """Load candle data for the chart."""
        if self._current_symbol_id is None:
            return
        self._current_interval = interval
        cache_key = f"{self._current_symbol_id}:{interval}:{days}"
        if cache_key in self._candle_cache:
            self._draw_candles(self._candle_cache[cache_key])
            return

        self._chart_status.configure(text="Loading...")
        sid = self._current_symbol_id
        threading.Thread(
            target=self._fetch_candles_worker,
            args=(sid, interval, days, cache_key),
            daemon=True,
        ).start()

    def _fetch_candles_worker(
        self, symbol_id: int, interval: str, days: int, cache_key: str,
    ) -> None:
        """Background thread to fetch candle data."""
        try:
            from questrade.api.auth import get_initial_tokens
            from questrade.api.candles import fetch_candles
            from questrade.api.client import build_client

            tokens = get_initial_tokens()
            client = build_client(tokens.access_token, tokens.api_server)
            end = datetime.now(tz=UTC)
            start = end - timedelta(days=days)
            candles = fetch_candles(symbol_id, start, end, interval, client)
            self.after(0, self._on_candles_loaded, candles, cache_key)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_candles_error, str(exc))

    def _on_candles_loaded(
        self, candles: list[object], cache_key: str,
    ) -> None:
        self._candle_cache[cache_key] = candles
        self._chart_status.configure(text=f"{len(candles)} candles")
        self._draw_candles(candles)

    def _on_candles_error(self, msg: str) -> None:
        self._chart_status.configure(text=f"Error: {msg[:40]}")

    def _draw_candles(self, candles: list[object]) -> None:
        """Draw OHLC candlestick chart on the canvas."""
        from questrade.models.candle import Candle

        canvas = self._chart_canvas
        canvas.delete("all")
        canvas.update_idletasks()

        typed: list[Candle] = [c for c in candles if isinstance(c, Candle)]
        if not typed:
            canvas.create_text(
                200, 90, text="No candle data available",
                fill=CLR_TEXT_DIM, font=(FONT_FAMILY, 10),
            )
            return

        w = canvas.winfo_width() or 600
        h = canvas.winfo_height() or 180
        pad_top, pad_bot = 10, 30
        pad_left, pad_right = 50, 10

        all_highs = [c.high for c in typed]
        all_lows = [c.low for c in typed]
        price_max = max(all_highs)
        price_min = min(all_lows)
        price_range = price_max - price_min
        if price_range == 0:
            price_range = 1.0

        chart_w = w - pad_left - pad_right
        chart_h = h - pad_top - pad_bot
        n = len(typed)
        candle_w = max(1, chart_w / n)
        body_w = max(1, candle_w * 0.6)

        def y_for_price(p: float) -> float:
            return pad_top + (1 - (p - price_min) / price_range) * chart_h

        # Draw price grid lines
        for i in range(5):
            price = price_min + price_range * i / 4
            y = y_for_price(price)
            canvas.create_line(
                pad_left, y, w - pad_right, y, fill=CLR_BORDER, dash=(2, 4),
            )
            canvas.create_text(
                pad_left - 4, y, text=f"${price:,.2f}",
                fill=CLR_TEXT_DIM, font=(FONT_FAMILY, 7), anchor=tk.E,
            )

        # Draw volume histogram at the bottom
        max_vol = max((c.volume for c in typed), default=1) or 1
        vol_height = pad_bot - 5
        for i, c in enumerate(typed):
            x = pad_left + i * candle_w + candle_w / 2
            vol_h = (c.volume / max_vol) * vol_height
            color = CLR_GREEN if c.close >= c.open else CLR_RED
            canvas.create_rectangle(
                x - body_w / 2, h - vol_h, x + body_w / 2, h,
                fill=color, outline="", stipple="gray25",
            )

        # Draw candles
        for i, c in enumerate(typed):
            x = pad_left + i * candle_w + candle_w / 2
            y_open = y_for_price(c.open)
            y_close = y_for_price(c.close)
            y_high = y_for_price(c.high)
            y_low = y_for_price(c.low)

            color = CLR_GREEN if c.close >= c.open else CLR_RED

            # Wick
            canvas.create_line(x, y_high, x, y_low, fill=color, width=1)

            # Body
            body_top = min(y_open, y_close)
            body_bot = max(y_open, y_close)
            if body_bot - body_top < 1:
                body_bot = body_top + 1
            canvas.create_rectangle(
                x - body_w / 2, body_top, x + body_w / 2, body_bot,
                fill=color, outline=color,
            )

    # -- Range bar helper --

    def _draw_range_bar(
        self, canvas: tk.Canvas, low: float, high: float, current: float,
    ) -> None:
        """Draw a day range bar with a marker for the current price."""
        canvas.delete("all")
        canvas.update_idletasks()
        w = canvas.winfo_width() or 300
        h = canvas.winfo_height() or 14
        pad = 2

        canvas.create_rectangle(
            pad, 4, w - pad, h - 4, fill=CLR_BORDER, outline="",
        )

        if high > low:
            ratio = (current - low) / (high - low)
            ratio = max(0.0, min(1.0, ratio))
            fill_x = pad + ratio * (w - 2 * pad)
            canvas.create_rectangle(
                pad, 4, fill_x, h - 4, fill=CLR_ACCENT, outline="",
            )
            canvas.create_line(
                fill_x, 1, fill_x, h - 1, fill=CLR_TEXT_BRIGHT, width=2,
            )
