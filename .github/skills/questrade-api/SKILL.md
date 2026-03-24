# Questrade API Skill (Python)

> Reusable domain knowledge for the Questrade REST API.
> Reference with `#questrade-api` in Copilot Chat.

---

## When to Use

Invoke when any task involves Questrade OAuth, symbol resolution, quote fetching,
or Questrade-specific error codes.

---

## Authentication

```
POST https://login.questrade.com/oauth2/token
  ?grant_type=refresh_token
  &refresh_token={token}
```

| Response Field | Notes |
|----------------|-------|
| `access_token` | Add as `Authorization: Bearer {token}` header |
| `refresh_token` | **Rotates — persist immediately** |
| `api_server` | Dynamic base URL — never hardcode |
| `expires_in` | Seconds until expiry (1800 typical) |

---

## Symbol Resolution

```
GET {api_server}/v1/symbols/search?prefix={symbol}
Authorization: Bearer {access_token}
```

Exact match required on BOTH `symbol` AND `listingExchange`:

| Ticker | `listingExchange` |
|--------|-------------------|
| MSFT   | `NASDAQ`          |
| FIE.TO  | `TSX`             |
| XEQT.TO | `TSX`             |

---

## Quote Fetching (always batch)

```
GET {api_server}/v1/markets/quotes?ids={id1},{id2},{id3}
Authorization: Bearer {access_token}
```

### Pydantic Model

```python
class Quote(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    symbol_id: int                 = Field(alias="symbolId")
    last_trade_price: float | None = Field(alias="lastTradePrice")
    last_trade_time: str           = Field(alias="lastTradeTime")
    bid_price: float               = Field(alias="bidPrice")
    ask_price: float               = Field(alias="askPrice")
    volume: int
    delay: int
    is_halted: bool                = Field(alias="isHalted")
```

### Price Priority

1. Use `last_trade_price` — the canonical trade price
2. If `last_trade_price is None` → report `N/A — no trades recorded`
3. Never substitute `bid_price` or `ask_price` as the primary price

---

## Error Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 401 | Token expired | Refresh once, retry |
| 429 | Rate limit | Wait `Retry-After` seconds, retry once |
| 400 | Bad request | Log + raise, no retry |
| 500 | Server error | Log + raise, no retry |

---

## Rate Limits

- Max ~20 requests/minute
- Add 250 ms delay between sequential non-batched calls
- Batching all quotes in one `?ids=` call counts as one request

---

## Market Hours (Eastern Time)

| Market | Hours |
|--------|-------|
| TSX    | 9:30 AM – 4:00 PM ET, Mon–Fri |
| NASDAQ | 9:30 AM – 4:00 PM ET, Mon–Fri |

---

## Python Type Reference

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
    api_server: str
    expires_in: int
    expires_at: datetime

@dataclass
class SymbolConfig:
    symbol: str
    exchange: str
    name: str
```
