# Add New Security Symbol

> **Usage:** Attach in Copilot Chat when adding a new ticker. Invoke with `/add-symbol`.

---

## Input Required

Confirm these values before generating code:

1. **Ticker symbol** — e.g. `AAPL`, `VFV`, `ZSP`
2. **Exchange** — `NASDAQ`, `NYSE`, `TSX`, or `TSXV`
3. **Security name** — full human-readable name

If any are missing, ask the user before proceeding.

## Tasks

### 1. Update `symbols.json`

Add the new entry to the JSON array in `symbols.json`:

```json
{ "symbol": "{SYMBOL}", "exchange": "{EXCHANGE}", "name": "{FULL NAME}" }
```

TSX-listed securities require the `.TO` suffix (e.g. `FIE.TO`, `XEQT.TO`).

### 2. Add Test in `tests/unit/test_symbols.py`

```python
def test_resolves_{symbol_lower}_on_{exchange_lower}(httpx_mock):
    httpx_mock.add_response(
        url__contains="symbols/search",
        json={"symbols": [{"symbol": "{SYMBOL}", "symbolId": 99999, "listingExchange": "{EXCHANGE}", "description": "{FULL NAME}"}]},
    )
    result = resolve_symbol_id("{SYMBOL}", "{EXCHANGE}")
    assert result == 99999
```

### 3. Update README.md

Update the watchlist example in the README if desired.

## Checklist

- [ ] `symbols.json` updated with new entry
- [ ] New symbol test added and passing (`pytest tests/unit/test_symbols.py`)
- [ ] README updated (if desired)
- [ ] All existing tests still pass (`pytest`)
