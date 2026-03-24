# Implement Token Refresh

> **Usage:** Attach in Copilot Chat when scaffolding OAuth logic. Invoke with `/refresh-token`.

---

Implement or fix the Questrade OAuth 2.0 token refresh flow in `src/questrade/api/auth.py`.

## OAuth Endpoint

```
POST https://login.questrade.com/oauth2/token
  ?grant_type=refresh_token
  &refresh_token={current_refresh_token}
```

## Expected Response

```json
{
  "access_token":  "...",
  "refresh_token": "...",   ← rotates on every call
  "api_server":    "https://api01.iq.questrade.com/",
  "token_type":    "Bearer",
  "expires_in":    1800
}
```

## Pydantic Response Model

```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    api_server: str
    token_type: str
    expires_in: int
```

## AuthTokens Dataclass

```python
@dataclass
class AuthTokens:
    access_token: str
    refresh_token: str
    api_server: str        # always ensure trailing slash
    expires_in: int
    expires_at: datetime   # datetime.now(tz=UTC) + timedelta(seconds=expires_in)
```

## Function Signature

```python
def refresh_token(current_refresh_token: str) -> AuthTokens:
    """Refreshes the Questrade access token.

    Args:
        current_refresh_token: The current long-lived refresh token.

    Returns:
        Fresh AuthTokens with rotated credentials.

    Raises:
        TokenRefreshError: On any HTTP or network failure.
    """
```

## Token Rotation

After a successful refresh, call:
```python
from questrade.config import persist_env
persist_env("QUESTRADE_REFRESH_TOKEN", tokens.refresh_token)
persist_env("QUESTRADE_API_SERVER", tokens.api_server)
```

## Security Rules

- Never log `access_token` or `refresh_token` values
- Log only: `f"Token refreshed. Expires at: {tokens.expires_at.isoformat()}"`

## Error Handling

```python
except httpx.HTTPStatusError as exc:
    raise TokenRefreshError(
        f"Token refresh failed with status {exc.response.status_code}"
    ) from exc
except httpx.RequestError as exc:
    raise TokenRefreshError(f"Network error during token refresh: {exc}") from exc
```
