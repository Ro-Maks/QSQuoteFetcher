---
applyTo: "tests/**"
---

# Testing Instructions

Applied when Copilot edits any file under `tests/`.

## Framework & Plugins

- **Runner:** `pytest`
- **HTTP mocking:** `pytest-httpx` — mock `httpx` calls without patching
- **Coverage:** `pytest-cov` — target ≥ 80% line coverage on `src/questrade/`
- **Fixtures:** shared fixtures in `tests/fixtures/quote_fixtures.py`

## Test Structure — AAA Pattern

```python
def test_fetch_quotes_returns_prices(httpx_mock):
    # Arrange
    httpx_mock.add_response(
        url__contains="/v1/markets/quotes",
        json=mock_quote_response(),
    )

    # Act
    quotes = fetch_quotes([10001, 20001, 30001])

    # Assert
    assert len(quotes) == 3
    assert all(q.last_trade_price is not None for q in quotes)
```

## Required Test Cases

### `test_auth.py`

- ✅ Successful refresh returns valid `AuthTokens`
- ✅ `refresh_token` field is rotated (new value differs from input)
- ✅ `api_server` always has a trailing slash
- ✅ `expires_at` is approximately `now + expires_in` seconds
- ✅ HTTP 401 raises `TokenRefreshError`
- ✅ Network error raises `TokenRefreshError`

### `test_symbols.py`

- ✅ MSFT resolves correctly against NASDAQ
- ✅ FIE.TO resolves correctly against TSX
- ✅ XEQT.TO resolves correctly against TSX
- ✅ Unknown symbol raises `SymbolNotFoundError`
- ✅ FIE.TO on wrong exchange (NASDAQ) raises `SymbolNotFoundError`

### `test_quotes.py`

- ✅ All three symbol IDs are batched into one request
- ✅ `last_trade_price` is non-None for all symbols
- ✅ `delay > 0` is surfaced with a warning (no exception)
- ✅ `is_halted=True` is surfaced with a warning (no exception)
- ✅ `last_trade_price=None` raises `QuoteUnavailableError`
- ✅ HTTP 500 raises `QuestradeApiError`
- ✅ Empty `symbol_ids` list raises `ValueError`

## Mocking Rules

- Never make real HTTP calls in unit tests — always use `pytest-httpx`
- Never use real tokens in test fixtures — use `"mock-access-token"` etc.
- Use `pytest.raises(ExceptionType)` for all exception assertions

## Fixture File

All shared mock data lives in `tests/fixtures/quote_fixtures.py`:

```python
def mock_quote_response(overrides: dict | None = None) -> dict:
    base = {
        "quotes": [
            {"symbol": "MSFT", "symbolId": 10001, "lastTradePrice": 415.23, ...},
            ...
        ]
    }
    if overrides:
        base.update(overrides)
    return base
```

## File Naming

- Unit tests: `tests/unit/test_{module}.py`
- Fixtures: `tests/fixtures/quote_fixtures.py`
