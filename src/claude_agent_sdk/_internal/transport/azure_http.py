"""Azure OpenAI APIM HTTP transport implementation."""

import json
import logging
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

import aiohttp

from ..._errors import CLIConnectionError
from ...types import AzureOpenAIOptions
from ..auth.azure_auth import AzureADAuth
from . import Transport

logger = logging.getLogger(__name__)


class AzureHTTPTransport(Transport):
    """HTTP transport for Azure OpenAI APIM with enterprise authentication."""

    def __init__(
        self,
        prompt: str | AsyncIterable[dict[str, Any]],
        options: AzureOpenAIOptions,
    ):
        """Initialize Azure HTTP transport.

        Args:
            prompt: Initial prompt or stream of messages
            options: Azure OpenAI configuration options
        """
        self._prompt = prompt
        self._is_streaming = not isinstance(prompt, str)
        self._options = options
        self._session: aiohttp.ClientSession | None = None
        self._ready = False

        # Initialize Azure AD authentication
        self._auth = AzureADAuth(
            tenant_id=options.tenant_id,
            client_id=options.client_id,
            client_secret=options.client_secret,
            scope=options.scope or "https://cognitiveservices.azure.com/.default",
        )

        # Construct the full endpoint URL
        # Format: https://{apim-instance}.azure-api.net/{api-path}/chat/completions
        self._endpoint_url = f"{options.endpoint.rstrip('/')}/chat/completions"

        # Store APIM subscription key
        self._apim_subscription_key = options.apim_subscription_key

    async def connect(self) -> None:
        """Establish HTTP session and validate credentials."""
        if self._session:
            return

        try:
            # Create aiohttp session
            self._session = aiohttp.ClientSession()

            # Validate authentication by getting a token
            await self._auth.get_access_token()

            self._ready = True
            logger.info("Successfully connected to Azure OpenAI APIM")

        except Exception as e:
            error = CLIConnectionError(f"Failed to connect to Azure OpenAI: {e}")
            await self._cleanup_session()
            raise error from e

    async def _cleanup_session(self) -> None:
        """Clean up HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def close(self) -> None:
        """Close the transport and clean up resources."""
        self._ready = False
        await self._cleanup_session()

    async def write(self, data: str) -> None:
        """Write data (not used in HTTP mode, raises error)."""
        raise NotImplementedError(
            "write() is not supported for Azure HTTP transport. "
            "Use read_messages() to get streaming responses."
        )

    async def end_input(self) -> None:
        """End input stream (no-op for HTTP)."""
        pass

    def read_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Read and parse messages from Azure OpenAI."""
        return self._read_messages_impl()

    async def _read_messages_impl(self) -> AsyncIterator[dict[str, Any]]:
        """Internal implementation of read_messages."""
        if not self._ready or not self._session:
            raise CLIConnectionError("Not connected to Azure OpenAI")

        try:
            # Get access token
            access_token = await self._auth.get_access_token()

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }

            # Add APIM subscription key header if provided
            if self._apim_subscription_key:
                headers["Ocp-Apim-Subscription-Key"] = self._apim_subscription_key

            # Prepare request body
            messages = self._prepare_messages()
            request_body = {
                "messages": messages,
                "stream": True,
                "model": self._options.model or "gpt-4",
                "max_tokens": self._options.max_tokens,
            }

            # Add optional parameters
            if self._options.temperature is not None:
                request_body["temperature"] = self._options.temperature

            if self._options.tools:
                request_body["tools"] = self._options.tools

            # Make streaming request
            async with self._session.post(
                self._endpoint_url,
                headers=headers,
                json=request_body,
            ) as response:
                response.raise_for_status()

                # Process Server-Sent Events stream
                async for line in response.content:
                    line_str = line.decode("utf-8").strip()

                    if not line_str:
                        continue

                    # Skip SSE comment lines
                    if line_str.startswith(":"):
                        continue

                    # Parse SSE data
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Remove "data: " prefix

                        # Check for stream end
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            # Convert Azure OpenAI format to SDK format
                            message = self._convert_chunk_to_message(chunk)
                            if message:
                                yield message
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse chunk: {e}")
                            continue

            # Yield final result message
            yield {
                "type": "result",
                "subtype": "end",
                "duration_ms": 0,
                "duration_api_ms": 0,
                "is_error": False,
                "num_turns": 1,
                "session_id": "azure",
            }

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during Azure OpenAI request: {e}")
            raise CLIConnectionError(f"Azure OpenAI API error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during Azure OpenAI request: {e}")
            raise CLIConnectionError(f"Unexpected error: {e}") from e

    def _prepare_messages(self) -> list[dict[str, Any]]:
        """Prepare messages array for Azure OpenAI API.

        Returns:
            List of message dictionaries in Azure OpenAI format
        """
        if isinstance(self._prompt, str):
            return [{"role": "user", "content": self._prompt}]

        # For streaming prompts, we'd need to accumulate them
        # For now, convert simple string prompt
        return [{"role": "user", "content": str(self._prompt)}]

    def _convert_chunk_to_message(self, chunk: dict[str, Any]) -> dict[str, Any] | None:
        """Convert Azure OpenAI stream chunk to SDK message format.

        Args:
            chunk: Azure OpenAI stream chunk

        Returns:
            SDK-formatted message or None if no content
        """
        choices = chunk.get("choices", [])
        if not choices:
            return None

        delta = choices[0].get("delta", {})
        role = delta.get("role")
        content = delta.get("content")
        tool_calls = delta.get("tool_calls")

        # Build message based on delta type
        if role == "assistant" and (content or tool_calls):
            message: dict[str, Any] = {
                "type": "assistant",
                "message": {
                    "content": [],
                    "model": chunk.get("model", self._options.model or "gpt-4"),
                },
            }

            # Add text content
            if content:
                message["message"]["content"].append({"type": "text", "text": content})

            # Add tool calls
            if tool_calls:
                for tool_call in tool_calls:
                    if tool_call.get("function"):
                        function = tool_call["function"]
                        message["message"]["content"].append(
                            {
                                "type": "tool_use",
                                "id": tool_call.get("id", ""),
                                "name": function.get("name", ""),
                                "input": json.loads(function.get("arguments", "{}")),
                            }
                        )

            return message

        return None

    def is_ready(self) -> bool:
        """Check if transport is ready for communication."""
        return self._ready
