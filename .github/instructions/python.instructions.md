---
applyTo: "**/*.py"
---

# Python Coding Standards

## Type Annotations

- Every function must annotate all parameters and return type
- Use `X | Y` union syntax (Python 3.10+) instead of `Optional[X]` or `Union[X, Y]`
- Use `list[T]`, `dict[K, V]`, `tuple[T, ...]` (lowercase) not `List`, `Dict`, `Tuple`
- Never use `Any` — use `object` for truly unknown types, then narrow with `isinstance`

```python
# CORRECT
def resolve_symbol_id(symbol: str, exchange: str) -> int:
    ...

# INCORRECT
def resolve_symbol_id(symbol, exchange):
    ...
```

## Naming Conventions

| Construct | Convention | Example |
|-----------|-----------|---------|
| Variables / functions | snake_case | `fetch_quotes`, `symbol_id` |
| Classes | PascalCase | `QuestradeClient`, `AuthTokens` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `TOKEN_URL` |
| Private helpers | `_leading_underscore` | `_validate_quotes` |
| Modules / files | snake_case | `quote_formatter.py` |

## Pydantic Models

All API response shapes must be Pydantic `BaseModel` subclasses with `model_config`:

```python
from pydantic import BaseModel, ConfigDict

class Quote(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    symbol_id: int = Field(alias="symbolId")
    last_trade_price: float | None = Field(alias="lastTradePrice")
    last_trade_time: str = Field(alias="lastTradeTime")
    bid_price: float = Field(alias="bidPrice")
    ask_price: float = Field(alias="askPrice")
    delay: int
    is_halted: bool = Field(alias="isHalted")
```

Use `alias=` to map camelCase Questrade API fields to snake_case Python attributes.

## Docstrings

All public functions and classes require Google-style docstrings:

```python
def fetch_quotes(symbol_ids: list[int], api_server: str, access_token: str) -> list[Quote]:
    """Fetches Level 1 quotes for the given symbol IDs in a single batched call.

    Args:
        symbol_ids: List of Questrade integer symbol IDs.
        api_server: Dynamic Questrade API base URL.
        access_token: Valid Bearer token for the Authorization header.

    Returns:
        List of validated Quote objects.

    Raises:
        QuoteUnavailableError: If last_trade_price is None for any symbol.
        QuestradeApiError: On any non-401 HTTP error from the API.
    """
```

## Error Handling

```python
# CORRECT — specific, typed, re-raises with context
try:
    response = client.get(url)
    response.raise_for_status()
except httpx.HTTPStatusError as exc:
    raise QuestradeApiError(
        f"Quote fetch failed: {exc.response.status_code}"
    ) from exc

# INCORRECT — swallows context, too broad
try:
    response = client.get(url)
except Exception:
    print("error")
```

## Environment Variables

Always use `get_env()` from `src/questrade/config.py`:

```python
# CORRECT
from questrade.config import get_env
token = get_env("QUESTRADE_REFRESH_TOKEN")

# INCORRECT
import os
token = os.environ["QUESTRADE_REFRESH_TOKEN"]
```

## f-strings and Formatting

- Use f-strings for string interpolation — not `%` or `.format()`
- Use `logging` module for diagnostic output — not `print()` inside library modules
- `print()` is acceptable only in `main.py` and `formatter.py`
