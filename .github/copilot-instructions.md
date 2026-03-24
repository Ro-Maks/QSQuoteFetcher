# Copilot Instructions — Questrade Price Fetcher (Python)

Applied automatically to every GitHub Copilot Chat session in this repository.

---

## Project Context

**Python 3.11+** project calling the **Questrade REST API** for real-time
Level 1 market quotes on three securities:

| Symbol | Exchange | Type         |
|--------|----------|--------------|
| MSFT   | NASDAQ   | US Equity    |
| FIE.TO  | TSX      | Canadian ETF |
| XEQT.TO | TSX      | Canadian ETF |

The Questrade API uses **OAuth 2.0 with rotating refresh tokens**. The
`api_server` base URL is **dynamic** — always read it from the token response
or from `QUESTRADE_API_SERVER` in `.env`.

---

## Stack

- **Language:** Python 3.11+, fully type-annotated
- **HTTP client:** `httpx` (sync; supports async expansion)
- **Data models:** `pydantic` v2 with strict validation
- **Config / env:** `python-dotenv` via `src/questrade/config.py`
- **Testing:** `pytest` + `pytest-httpx` for HTTP mocking
- **Linting:** `ruff`
- **Type checking:** `mypy` (strict mode)

---

## Coding Standards

- All functions must have full type annotations (parameters and return type)
- Use `pydantic.BaseModel` for every API request/response shape
- Use dataclasses (`@dataclass`) for internal value objects that don't need validation
- Prefer early returns for guard clauses
- Never use `Any` from `typing` — use specific types or `Union`
- Never call `os.environ` directly — use `get_env()` from `config.py`
- Never use bare `except:` — always catch a specific exception type

---

## Questrade API Quick Reference

### Authentication

```
POST https://login.questrade.com/oauth2/token
  ?grant_type=refresh_token
  &refresh_token={QUESTRADE_REFRESH_TOKEN}
```

Store from response: `access_token`, `refresh_token` (rotated!), `api_server`

### Symbol Resolution

```
GET {api_server}/v1/symbols/search?prefix={symbol}
Authorization: Bearer {access_token}
```

Match exact `symbol` AND correct `listingExchange` (MSFT→NASDAQ, FIE.TO→TSX, XEQT.TO→TSX).

### Batch Quote Fetch — always one call, never per-symbol

```
GET {api_server}/v1/markets/quotes?ids={id1},{id2},{id3}
Authorization: Bearer {access_token}
```

### Key Quote Fields

| Field             | Type           | Notes                          |
|-------------------|----------------|--------------------------------|
| `last_trade_price`| float \| None  | Primary price — report this    |
| `last_trade_time` | str            | ISO 8601 timestamp             |
| `bid_price`       | float          | Supplementary only             |
| `ask_price`       | float          | Supplementary only             |
| `delay`           | int            | 0 = real-time; >0 = delayed Nm |
| `is_halted`       | bool           | True = trading halted          |

---

## Output Format

```
[SYMBOL] | $[last_trade_price] | [last_trade_time] | [Real-Time | ⚠️ Delayed Nm] | Halted: [Y/N]
```

Flag delayed data with ⚠️. Flag halted securities with 🔴.

---

## What NOT to Do

- Do not hardcode `api_server`
- Do not call individual quote endpoints per symbol — always batch
- Do not return a price if `last_trade_price` is `None` — report the None explicitly
- Do not cache prices between runs
- Do not use `dict` where a Pydantic model should be used
