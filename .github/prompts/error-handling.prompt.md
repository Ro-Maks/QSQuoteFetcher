# Generate Error Handling

> **Usage:** Attach in Copilot Chat when adding error handling. Invoke with `/error-handling`.

---

Implement the typed exception hierarchy in `src/questrade/models/errors.py`.

## Exception Hierarchy

```python
class QuestradeApiError(Exception):
    """Base exception for all Questrade API failures."""
    def __init__(self, message: str, status_code: int | None = None, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.cause = cause


class SymbolNotFoundError(QuestradeApiError):
    """Raised when symbol + exchange lookup returns no match."""
    def __init__(self, symbol: str, exchange: str) -> None:
        super().__init__(f"Symbol '{symbol}' not found on exchange '{exchange}'")


class QuoteUnavailableError(QuestradeApiError):
    """Raised when last_trade_price is None (no trades recorded)."""
    def __init__(self, symbol: str) -> None:
        super().__init__(f"No trade price available for '{symbol}'")


class TokenRefreshError(QuestradeApiError):
    """Raised when the OAuth token refresh call fails."""


class RateLimitError(QuestradeApiError):
    """Raised when Questrade returns HTTP 429."""
    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after_seconds or '?'}s",
            status_code=429,
        )
        self.retry_after_seconds = retry_after_seconds
```

## Per-Module Usage

### `api/auth.py`

```python
except httpx.HTTPStatusError as exc:
    raise TokenRefreshError(
        f"HTTP {exc.response.status_code}", exc.response.status_code, exc
    ) from exc
except httpx.RequestError as exc:
    raise TokenRefreshError("Network error", cause=exc) from exc
```

### `api/quotes.py`

```python
for quote in quotes:
    if quote.last_trade_price is None:
        raise QuoteUnavailableError(quote.symbol)
    if quote.delay > 0:
        logging.warning("⚠️  %s: data delayed by %d minute(s)", quote.symbol, quote.delay)
    if quote.is_halted:
        logging.warning("🔴 %s: trading is halted", quote.symbol)
```

### Rate Limit (HTTP 429)

```python
if exc.response.status_code == 429:
    retry_after = int(exc.response.headers.get("retry-after", 60))
    raise RateLimitError(retry_after) from exc
```

## Top-Level Handler in `main.py`

```python
except TokenRefreshError:
    print("❌ Authentication failed — check QUESTRADE_REFRESH_TOKEN in .env")
except SymbolNotFoundError as e:
    print(f"❌ Symbol config error: {e}")
except QuoteUnavailableError as e:
    print(f"❌ Price unavailable: {e}")
except RateLimitError as e:
    print(f"❌ Rate limited: {e}")
except QuestradeApiError as e:
    print(f"❌ API error [{e.status_code}]: {e}")
```

## Rules

- All custom exceptions must inherit from `QuestradeApiError`
- Always preserve the original exception with `raise X from exc`
- Never use bare `except:` or `except Exception:` without re-raising
- Raise, never return error codes or `None` to signal failures
