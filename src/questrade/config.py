"""Configuration and environment variable management.

All environment variable access must go through this module.
Never call os.environ directly in other modules.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from questrade.models.symbol import SymbolConfig

# Load .env file on import
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"


def _load_dotenv() -> None:
    """Parse .env file into os.environ (minimal implementation, no extra deps)."""
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            if key not in os.environ:
                os.environ[key] = value


_load_dotenv()


def get_env(key: str) -> str:
    """Read a required environment variable.

    Args:
        key: The environment variable name.

    Returns:
        The string value of the variable.

    Raises:
        EnvironmentError: If the variable is missing or empty.
    """
    value = os.environ.get(key, "").strip()
    if not value:
        raise OSError(
            f"Missing required environment variable: {key}. "
            f"Check your .env file (see .env.example for reference)."
        )
    return value


def get_optional_env(key: str, fallback: str = "") -> str:
    """Read an optional environment variable.

    Args:
        key: The environment variable name.
        fallback: Value to return if the variable is absent.

    Returns:
        The string value, or fallback if not set.
    """
    return os.environ.get(key, fallback).strip()


def persist_env(key: str, value: str) -> None:
    """Write or update a key=value pair in the .env file.

    Used to persist the rotated refresh_token and updated api_server
    after every successful OAuth token refresh.

    Args:
        key: The environment variable name.
        value: The new value to store.
    """
    os.environ[key] = value

    if not _ENV_PATH.exists():
        _ENV_PATH.write_text(f"{key}={value}\n", encoding="utf-8")
        return

    content = _ENV_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)

    if pattern.search(content):
        content = pattern.sub(f"{key}={value}", content)
    else:
        content = content.rstrip("\n") + f"\n{key}={value}\n"

    _ENV_PATH.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Target securities configuration
# Edit symbols.json in the project root to manage your watchlist.
# ---------------------------------------------------------------------------

_SYMBOLS_PATH = Path(__file__).parent.parent.parent / "symbols.json"


def load_symbols() -> list[SymbolConfig]:
    """Load target symbols from symbols.json.

    Returns:
        List of SymbolConfig objects.

    Raises:
        EnvironmentError: If symbols.json is missing or malformed.
    """
    if not _SYMBOLS_PATH.exists():
        raise OSError(
            f"symbols.json not found at {_SYMBOLS_PATH}. "
            "Create a symbols.json file in the project root — see README."
        )
    try:
        data = json.loads(_SYMBOLS_PATH.read_text(encoding="utf-8"))
        return [SymbolConfig(**entry) for entry in data]
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        raise OSError(f"Invalid symbols.json: {exc}") from exc


TARGET_SYMBOLS: list[SymbolConfig] = load_symbols()


def save_symbols(symbols: list[SymbolConfig]) -> None:
    """Persist the symbol list to symbols.json."""
    data: list[dict[str, object]] = []
    for s in symbols:
        entry: dict[str, object] = {
            "symbol": s.symbol, "exchange": s.exchange, "name": s.name,
        }
        if s.alert_above is not None:
            entry["alert_above"] = s.alert_above
        if s.alert_below is not None:
            entry["alert_below"] = s.alert_below
        data.append(entry)
    _SYMBOLS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def reload_symbols() -> list[SymbolConfig]:
    """Reload symbols from disk and update TARGET_SYMBOLS in-place."""
    fresh = load_symbols()
    TARGET_SYMBOLS.clear()
    TARGET_SYMBOLS.extend(fresh)
    return TARGET_SYMBOLS


# ---------------------------------------------------------------------------
# GUI settings persistence
# ---------------------------------------------------------------------------

_SETTINGS_PATH = Path(__file__).parent.parent.parent / "settings.json"

_DEFAULT_SETTINGS: dict[str, object] = {
    "window_geometry": "1200x500",
    "sort_column": "symbol",
    "sort_descending": False,
    "auto_refresh": False,
    "refresh_interval": 10,
    "alert_threshold": 3.0,
}


def load_settings() -> dict[str, object]:
    """Load GUI settings from settings.json, falling back to defaults."""
    if not _SETTINGS_PATH.exists():
        return dict(_DEFAULT_SETTINGS)
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        merged = dict(_DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, TypeError):
        return dict(_DEFAULT_SETTINGS)


def save_settings(settings: dict[str, object]) -> None:
    """Persist GUI settings to settings.json."""
    _SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8",
    )
