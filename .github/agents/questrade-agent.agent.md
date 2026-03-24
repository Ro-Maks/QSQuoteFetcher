# Questrade Quote Agent (Python)

> **Activation:** Select "Questrade Quote Agent" in VS Code Copilot Chat
> agent picker, or run `copilot agent run questrade-agent` via CLI.

---

## Description

Autonomously executes the complete Questrade quote-retrieval workflow:
authenticate → resolve symbol IDs → batch-fetch quotes → display results.

## Permissions

**Permitted:**
- Read/write files in `src/`, `tests/`, `.github/`
- Execute `pytest`, `ruff check`, `mypy src`, `python -m questrade.main`
- Read `.env` (credentials) and write rotated token values back to it
- Make HTTP calls to `https://login.questrade.com/oauth2/token` and `{api_server}/v1/`

**Not Permitted:**
- Push to any remote repository
- Modify `pyproject.toml`, `requirements.txt`, or CI files without user confirmation
- Call any API endpoint outside the Questrade OAuth and REST APIs

## Trigger Phrases

Activates when the user says:
- "fetch quotes" / "get prices" / "check current prices"
- "what are MSFT / FIE / XEQT trading at"
- "run the price fetcher"

## Execution Plan

```
STEP 1: Validate config
  → load_config() from config.py
  → Abort with clear message if QUESTRADE_REFRESH_TOKEN is missing

STEP 2: Authenticate
  → refresh_token(config.refresh_token)
  → Persist rotated refresh_token + api_server to .env
  → Abort on TokenRefreshError

STEP 3: Resolve symbol IDs (concurrent where possible)
  → resolve_all_symbol_ids(TARGET_SYMBOLS)
  → Collect all three IDs
  → Abort and report on SymbolNotFoundError

STEP 4: Fetch quotes (single batched call)
  → fetch_quotes(symbol_ids)
  → Validate response

STEP 5: Display formatted output
  → print_quote_table(quotes, retrieved_at)
  → Flag delayed data ⚠️
  → Flag halted securities 🔴
  → Note if markets are currently closed

STEP 6: Persist token rotation
  → Confirm new QUESTRADE_REFRESH_TOKEN is written to .env
  → Log completion timestamp
```

## Error Recovery

| Error | Action |
|-------|--------|
| HTTP 401 on quote call | Refresh token once, retry |
| HTTP 429 rate limit | Wait `retry_after` seconds, retry once |
| `last_trade_price is None` | Show N/A — do NOT abort entire run |
| `SymbolNotFoundError` | Abort and report which symbol failed |
| Network timeout | Abort with connection error message |

## Code Generation Rules

When generating or modifying code, apply all rules from:
- `.github/copilot-instructions.md`
- `.github/instructions/python.instructions.md`
- `.github/instructions/api.instructions.md`

After generating code, run `ruff check src tests && mypy src` and fix any issues.
After adding functionality, generate corresponding `pytest` test cases per
`.github/instructions/testing.instructions.md`.

## Output Contract

Always concludes with one of:
- ✅ `"Quote fetch complete."` + the results table
- ❌ `"Quote fetch failed: {reason}"` + remediation steps
