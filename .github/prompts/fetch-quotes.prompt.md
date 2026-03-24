# Fetch Current Security Quotes

> **Usage:** Attach in Copilot Chat or invoke with `/fetch-quotes` in VS Code.

---

Execute the full Questrade quote-retrieval workflow for MSFT, FIE, and XEQT.

## Step 1 — Load Config

Call `load_config()` from `src/questrade/config.py`.
If `QUESTRADE_REFRESH_TOKEN` is missing, stop and print:
`ERROR: Missing QUESTRADE_REFRESH_TOKEN. Check your .env file.`

## Step 2 — Refresh Access Token

```python
from questrade.api.auth import refresh_token
tokens = refresh_token(config.refresh_token)
```

Persist the new `refresh_token` and `api_server` to `.env` automatically.
If this fails, stop and print the exception message.

## Step 3 — Resolve Symbol IDs (parallel)

```python
from questrade.api.symbols import resolve_all_symbol_ids
from questrade.config import TARGET_SYMBOLS
symbol_ids = resolve_all_symbol_ids(TARGET_SYMBOLS)
```

Abort and report which symbol failed if `SymbolNotFoundError` is raised.

## Step 4 — Batch Fetch Quotes

```python
from questrade.api.quotes import fetch_quotes
retrieved_at = datetime.now(tz=timezone.utc)
quotes = fetch_quotes(symbol_ids)
```

One API call. Never loop per symbol.

## Step 5 — Display Results

```python
from questrade.utils.formatter import print_quote_table
print_quote_table(quotes, retrieved_at)
```

Expected output format:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 QUESTRADE LIVE QUOTES  |  Retrieved: 2026-03-21T19:34:12Z
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MSFT   | $415.23  | 2026-03-21 3:34 PM ET | Real-Time     | ✅ Active
 FIE    | $8.92    | 2026-03-21 3:34 PM ET | Real-Time     | ✅ Active
 XEQT   | $31.47   | 2026-03-21 3:34 PM ET | Real-Time     | ✅ Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Rules

- If `last_trade_price` is `None`, print `N/A — no trades recorded` for that row
- Never fill in prices from memory — only API response data
- Note if markets are currently closed below the table
