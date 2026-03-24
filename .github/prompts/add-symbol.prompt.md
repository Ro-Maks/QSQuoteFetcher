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

### 1. Update `src/questrade/config.py`

Add the new entry to `TARGET_SYMBOLS`:

```python
TARGET_SYMBOLS: list[SymbolConfig] = [
    SymbolConfig(symbol="MSFT",  exchange="NASDAQ", name="Microsoft Corporation"),
    SymbolConfig(symbol="FIE",   exchange="TSX",    name="iShares Canadian Financial Monthly Income ETF"),
    SymbolConfig(symbol="XEQT",  exchange="TSX",    name="iShares Core Equity ETF Portfolio"),
    # ADD HERE:
    SymbolConfig(symbol="{SYMBOL}", exchange="{EXCHANGE}", name="{FULL NAME}"),
]
```

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

Add the new symbol to the **Target Securities** table.

### 4. Update AGENTS.md

Add the new symbol to the **Target Securities** section.

## Checklist

- [ ] `TARGET_SYMBOLS` list updated in `config.py`
- [ ] New symbol test added and passing (`pytest tests/unit/test_symbols.py`)
- [ ] README table updated
- [ ] AGENTS.md updated
- [ ] All existing tests still pass (`pytest`)
