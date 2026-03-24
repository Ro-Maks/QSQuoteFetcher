---
applyTo: "src/questrade/api/**"
---

# API Layer Instructions

Applied when Copilot edits any file under `src/questrade/api/`.

## Module Responsibilities

| Module | Single Responsibility |
|--------|-----------------------|
| `auth.py` | OAuth token refresh and `.env` rotation only |
| `client.py` | httpx session creation and 401 retry logic only |
| `symbols.py` | Symbol → symbolId resolution with in-process cache |
| `quotes.py` | Batched quote fetch and response validation only |

Do not mix authentication into quote fetching, or vice versa.

## auth.py

- Export a single `refresh_token(current_refresh_token: str) -> AuthTokens` function
- After a successful refresh, call `persist_tokens(tokens)` to rotate `.env`
- Never log token values — log only `"Token refreshed. Expires: {expires_at}"`
- Raise `TokenRefreshError` on any HTTP or network failure

## client.py

- Build an `httpx.Client` with `timeout=10.0` and `base_url` from config
- Inject `Authorization: Bearer {access_token}` via a custom `httpx.Auth` class
- On HTTP 401: call `refresh_token()` once, update the client auth, retry
- If the retry also returns 401: raise `TokenRefreshError` — do not loop
- On HTTP 429: raise `RateLimitError` with the `Retry-After` header value

## symbols.py

- Export `resolve_symbol_id(symbol: str, exchange: str) -> int`
- Cache resolved IDs in a module-level `dict[str, int]` (key: `"SYMBOL:EXCHANGE"`)
- Raise `SymbolNotFoundError` if no exact symbol + exchange match is found

## quotes.py

- Export `fetch_quotes(symbol_ids: list[int]) -> list[Quote]`
- Always join all IDs into one request: `?ids=1,2,3`
- Call `_validate_quotes(quotes)` before returning
- Raise `QuoteUnavailableError` if `last_trade_price is None` for any quote

## HTTP Conventions

```python
# Always use raise_for_status() immediately after a request
response = client.get(url)
response.raise_for_status()

# Always parse into a Pydantic model — never use response.json() raw
data = QuoteResponse.model_validate(response.json())
```

## Rate Limiting

Add a minimum 250 ms delay between sequential API calls in any loop.
Never exceed 20 requests per minute across all endpoints.
