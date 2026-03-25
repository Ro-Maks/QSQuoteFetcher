"""System tray integration and desktop notifications."""
from __future__ import annotations

import contextlib
import threading
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from questrade.gui.app import QuoteApp

_DEFAULT_ALERT_THRESHOLD = 3.0


def _create_tray_icon() -> Image.Image:
    """Create a simple 64x64 icon for the system tray."""
    img = Image.new("RGBA", (64, 64), (26, 29, 35, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], outline=(97, 175, 239, 255), width=5)
    draw.line([40, 40, 56, 56], fill=(97, 175, 239, 255), width=5)
    return img


class SystemTray:
    """Manages the system tray icon and notifications."""

    def __init__(self, app: QuoteApp, alert_threshold: float = _DEFAULT_ALERT_THRESHOLD) -> None:
        self._app = app
        self._icon: object = None
        self._prev_prices: dict[str, float] = {}
        self._fired_alerts: dict[str, set[str]] = {}
        self.alert_threshold = alert_threshold

    def start(self) -> None:
        """Start the system tray icon in a background thread."""
        try:
            import pystray

            icon = pystray.Icon(
                "QSQuoteFetcher",
                _create_tray_icon(),
                "Questrade Quote Fetcher",
                menu=pystray.Menu(
                    pystray.MenuItem("Show", self._on_show, default=True),
                    pystray.MenuItem("Refresh", self._on_refresh),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Quit", self._on_quit),
                ),
            )
            self._icon = icon
            threading.Thread(target=icon.run, daemon=True).start()
        except ImportError:
            pass

    def stop(self) -> None:
        """Stop the tray icon."""
        if self._icon is not None:
            with contextlib.suppress(Exception):
                self._icon.stop()  # type: ignore[union-attr]

    def check_alerts(self) -> None:
        """Check for big price moves and per-symbol alerts."""
        from questrade.config import TARGET_SYMBOLS

        # Build lookup for per-symbol alert config
        sym_cfg = {s.symbol: s for s in TARGET_SYMBOLS}

        for q in self._app._quotes:  # noqa: SLF001
            if q.last_trade_price is None:
                continue

            # Global % from open alert
            if q.open_price is not None and q.open_price != 0:
                pct = abs(
                    (q.last_trade_price - q.open_price) / q.open_price * 100,
                )
                prev_pct = self._prev_prices.get(q.symbol)
                if pct >= self.alert_threshold and (
                    prev_pct is None or prev_pct < self.alert_threshold
                ):
                    direction = "up" if q.last_trade_price > q.open_price else "down"
                    self._notify(
                        f"{q.symbol} Big Move",
                        f"{q.symbol} is {direction} {pct:.1f}% from open "
                        f"(${q.last_trade_price:,.2f})",
                    )
                self._prev_prices[q.symbol] = pct

            # Per-symbol price target alerts
            cfg = sym_cfg.get(q.symbol)
            if cfg is None:
                continue
            fired = self._fired_alerts.setdefault(q.symbol, set())

            if cfg.alert_above is not None:
                if q.last_trade_price >= cfg.alert_above:
                    if "above" not in fired:
                        fired.add("above")
                        self._notify(
                            f"{q.symbol} Above ${cfg.alert_above:,.2f}",
                            f"{q.symbol} hit ${q.last_trade_price:,.2f} "
                            f"(target: ${cfg.alert_above:,.2f})",
                        )
                else:
                    fired.discard("above")

            if cfg.alert_below is not None:
                if q.last_trade_price <= cfg.alert_below:
                    if "below" not in fired:
                        fired.add("below")
                        self._notify(
                            f"{q.symbol} Below ${cfg.alert_below:,.2f}",
                            f"{q.symbol} dropped to ${q.last_trade_price:,.2f} "
                            f"(target: ${cfg.alert_below:,.2f})",
                        )
                else:
                    fired.discard("below")

    def _notify(self, title: str, message: str) -> None:
        """Send a desktop notification via the tray icon."""
        if self._icon is not None:
            with contextlib.suppress(Exception):
                self._icon.notify(message, title)  # type: ignore[union-attr]

    def _on_show(self) -> None:
        self._app.after(0, self._app.deiconify)

    def _on_refresh(self) -> None:
        self._app.after(0, self._app.refresh_quotes)

    def _on_quit(self) -> None:
        self.stop()
        self._app.after(0, self._app._on_close)  # noqa: SLF001
