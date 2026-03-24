"""Main entry point for the Questrade Price Fetcher.

Run with:
    python -m questrade.main
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from questrade.api.auth import get_initial_tokens
from questrade.api.client import build_client
from questrade.api.quotes import fetch_quotes
from questrade.api.symbols import resolve_all_symbol_ids
from questrade.config import TARGET_SYMBOLS
from questrade.models.errors import (
    QuestradeApiError,
    QuoteUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
    TokenRefreshError,
)
from questrade.models.quote import Quote
from questrade.utils.formatter import print_quote_table

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_all_quotes() -> tuple[list[Quote], datetime]:
    """Authenticate, resolve symbols, and fetch quotes.

    Returns:
        Tuple of (list of Quote objects, UTC datetime of retrieval).
    """
    tokens = get_initial_tokens()
    client = build_client(tokens.access_token, tokens.api_server)
    symbol_ids = resolve_all_symbol_ids(TARGET_SYMBOLS, client)
    retrieved_at = datetime.now(tz=timezone.utc)
    quotes = fetch_quotes(symbol_ids, client)
    return quotes, retrieved_at


def run() -> None:
    """Execute the full price-fetch workflow.

    Steps:
        1. Authenticate and obtain fresh tokens
        2. Resolve all target symbol IDs
        3. Batch-fetch quotes in a single API call
        4. Display formatted results table

    Raises:
        SystemExit: On any unrecoverable error.
    """
    print("🔄 Starting Questrade Price Fetcher...\n")

    # Step 1: Authenticate
    tokens = get_initial_tokens()
    client = build_client(tokens.access_token, tokens.api_server)

    # Step 2: Resolve symbol IDs
    symbol_names = ", ".join(s.symbol for s in TARGET_SYMBOLS)
    print(f"📋 Resolving symbol IDs for: {symbol_names}...")
    symbol_ids = resolve_all_symbol_ids(TARGET_SYMBOLS, client)

    resolved = ", ".join(
        f"{s.symbol}→{sid}" for s, sid in zip(TARGET_SYMBOLS, symbol_ids)
    )
    print(f"✅ Resolved: {resolved}\n")

    # Step 3: Batch fetch quotes
    print("📡 Fetching live quotes...")
    retrieved_at = datetime.now(tz=timezone.utc)
    quotes = fetch_quotes(symbol_ids, client)

    # Step 4: Display results
    print_quote_table(quotes, retrieved_at)


def main() -> None:
    """Top-level entry point with typed error handling."""
    try:
        run()
    except TokenRefreshError:
        print("\n❌ Authentication failed — check QUESTRADE_REFRESH_TOKEN in .env")
        sys.exit(1)
    except SymbolNotFoundError as exc:
        print(f"\n❌ Symbol configuration error: {exc}")
        sys.exit(1)
    except QuoteUnavailableError as exc:
        print(f"\n❌ Price unavailable: {exc}")
        sys.exit(1)
    except RateLimitError as exc:
        print(f"\n❌ Rate limited by Questrade API: {exc}")
        sys.exit(1)
    except QuestradeApiError as exc:
        print(f"\n❌ Questrade API error [{exc.status_code}]: {exc}")
        sys.exit(1)
    except EnvironmentError as exc:
        print(f"\n❌ Configuration error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
