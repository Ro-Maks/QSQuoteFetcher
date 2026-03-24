# AGENTS.md — Questrade Price Fetcher (Python)

> Recognized by GitHub Copilot CLI, Copilot Coding Agent, and third-party
> agents (OpenAI Codex, Devin, etc.). Provides root-level instructions for
> any AI agent operating in this repository.

## Project Purpose

This repository integrates with the **Questrade REST API** to fetch real-time
Level 1 market quotes. The workflow is:

1. Authenticate via OAuth 2.0 (refresh token grant)
2. Resolve ticker symbols → Questrade `symbolId` integers
3. Batch-fetch quotes via `GET /v1/markets/quotes?ids=`
4. Parse, validate, and surface `last_trade_price` for each security

## Target Securities

| Symbol  | Exchange | Type         |
|---------|----------|--------------|
| MSFT    | NASDAQ   | US Equity    |
| FIE.TO  | TSX      | Canadian ETF |
| XEQT.TO | TSX      | Canadian ETF |

> **Important:** The `.TO` suffix is required by the Questrade API for TSX-listed
> securities. Searching for `FIE` or `XEQT` without `.TO` will return no match.

## Agent Rules

### Must Always

- Use Python 3.11+ with full type annotations on all functions
- Use `httpx` for all HTTP requests
- Use `pydantic` v2 for all data models and response validation
- Load env vars through `src/questrade/config.py` — never call `os.environ` directly elsewhere
- Handle HTTP 401 by refreshing the token once before failing
- Validate that `last_trade_price` is not `None` before returning
- Log `delay` field — warn if `> 0` (data is delayed)
- Check `is_halted` on every quote and surface it in output
- Rotate and persist the new `refresh_token` and `api_server` after every auth call
- Use `float | None` for `bid_price` and `ask_price` — the Questrade API returns `None` for these outside market hours

### Must Never

- Cache or reuse prices from a previous session
- Guess or estimate prices — only use API response data
- Hardcode `api_server` — it is dynamic, returned by the OAuth endpoint
- Commit `.env` or any secrets file
- Call individual quote endpoints per symbol — always batch with `?ids=`
- Use bare `except:` without re-raising or typed handling
- Use `FIE` or `XEQT` as symbol strings — always use `FIE.TO` and `XEQT.TO`

## Commands

### With a virtual environment (recommended)

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m questrade.main

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m questrade.main
```

### Without a virtual environment (Windows — quick run)

```powershell
# Install dependencies to user site-packages, then run with PYTHONPATH set
pip install httpx pydantic
$env:PYTHONPATH = "src"
python -m questrade.main
```

### Other commands

```bash
pytest                             # Run all tests
pytest --cov=src --cov-fail-under=80
ruff check src tests               # Lint
mypy src                           # Type check
```

## Environment Variables

```
QUESTRADE_REFRESH_TOKEN=    # Long-lived refresh token
QUESTRADE_API_SERVER=       # Dynamic base URL (auto-updated after token refresh)
```

## Known Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'questrade'` | Running without venv and without `PYTHONPATH` set | Add `$env:PYTHONPATH = "src"` (PowerShell) or `PYTHONPATH=src` (bash) |
| `BackendUnavailable: Cannot import 'setuptools.backends.legacy'` | Python 3.14 pip incompatibility | Already fixed in `pyproject.toml` — uses `setuptools.build_meta` |
| `ValidationError` on `bidPrice` or `askPrice` | Questrade returns `None` for these outside market hours | Already fixed in `models/quote.py` — typed as `float \| None` |
| `SymbolNotFoundError` for `FIE` or `XEQT` | Wrong symbol name — Questrade requires `.TO` suffix | Use `FIE.TO` and `XEQT.TO` in `config.py` |
