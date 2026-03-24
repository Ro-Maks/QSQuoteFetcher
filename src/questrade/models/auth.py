"""Auth data models for Questrade OAuth token responses."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Raw OAuth token response from Questrade."""

    access_token: str
    refresh_token: str
    api_server: str
    token_type: str
    expires_in: int


@dataclass
class AuthTokens:
    """Processed auth credentials ready for use in API calls."""

    access_token: str
    refresh_token: str
    api_server: str       # always has a trailing slash
    expires_in: int
    expires_at: datetime  # UTC datetime when the access token expires

    @classmethod
    def from_response(cls, resp: TokenResponse) -> "AuthTokens":
        """Build AuthTokens from a raw TokenResponse.

        Args:
            resp: Validated Pydantic model from the OAuth endpoint.

        Returns:
            AuthTokens with expires_at calculated from the current UTC time.
        """
        server = resp.api_server
        if not server.endswith("/"):
            server += "/"

        return cls(
            access_token=resp.access_token,
            refresh_token=resp.refresh_token,
            api_server=server,
            expires_in=resp.expires_in,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(seconds=resp.expires_in),
        )
