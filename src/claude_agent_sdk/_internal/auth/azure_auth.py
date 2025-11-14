"""Azure AD OAuth2 authentication for Azure OpenAI APIM."""

import asyncio
import logging
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class AzureADAuth:
    """Handles Azure AD OAuth2 authentication with client credentials flow."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str = "https://cognitiveservices.azure.com/.default",
    ):
        """Initialize Azure AD authentication.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Application (client) ID
            client_secret: Client secret
            scope: OAuth2 scope (default: Azure Cognitive Services scope)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._token: str | None = None
        self._token_expiry: float = 0
        self._token_url = (
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        )
        self._refresh_lock = asyncio.Lock()

    def __repr__(self) -> str:
        """Return string representation without exposing client_secret."""
        return (
            f"AzureADAuth(tenant_id={self.tenant_id!r}, "
            f"client_id={self.client_id!r}, "
            f"scope={self.scope!r})"
        )

    async def get_access_token(self, session: aiohttp.ClientSession) -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            session: aiohttp ClientSession to use for HTTP requests

        Returns:
            Valid access token string

        Raises:
            aiohttp.ClientError: If token acquisition fails
            RuntimeError: If the access token cannot be acquired or response is invalid
        """
        # Check if we have a valid cached token (with 5 minute buffer)
        if self._token and time.time() < (self._token_expiry - 300):
            return self._token

        # Use lock to prevent concurrent token refreshes
        async with self._refresh_lock:
            # Check again after acquiring lock (another coroutine may have refreshed)
            if self._token and time.time() < (self._token_expiry - 300):
                return self._token

            # Request new token
            await self._refresh_token(session)
            if not self._token:
                raise RuntimeError("Failed to acquire access token")

            return self._token

    async def _refresh_token(self, session: aiohttp.ClientSession) -> None:
        """Refresh the access token using client credentials flow.

        Args:
            session: aiohttp ClientSession to use for HTTP requests
        """
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }

        try:
            async with session.post(self._token_url, data=data) as response:
                response.raise_for_status()
                token_data: dict[str, Any] = await response.json()

                self._token = token_data["access_token"]
                expires_in = int(token_data.get("expires_in", 3600))
                self._token_expiry = time.time() + expires_in

                logger.info("Successfully acquired Azure AD access token")

        except aiohttp.ClientError as e:
            logger.error(f"Failed to acquire Azure AD token: {type(e).__name__}")
            raise
        except KeyError as e:
            logger.error("Invalid token response format (missing required field)")
            raise RuntimeError("Invalid token response format") from e
