"""Azure OpenAI APIM HTTP transport implementation."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

from ..._errors import AzureConnectionError
from ...types import AzureOpenAIOptions
from ..auth.azure_auth import AzureADAuth
from . import Transport

logger = logging.getLogger(__name__)


class AzureHTTPTransport(Transport):
    """HTTP transport for Azure OpenAI APIM with enterprise authentication."""

    def __init__(
        self,
        prompt: str,
        options: AzureOpenAIOptions,
    ):
        """Initialize Azure HTTP transport.

        Args:
            prompt: Initial prompt string
            options: Azure OpenAI configuration options
        """
        self._prompt = prompt
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
            await self._auth.get_access_token(self._session)

            self._ready = True
            logger.info("Successfully connected to Azure OpenAI APIM")

        except Exception as e:
            error = AzureConnectionError(f"Failed to connect to Azure OpenAI: {e}")
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
            raise AzureConnectionError("Not connected to Azure OpenAI")

        try:
            # Get access token
            access_token = await self._auth.get_access_token(self._session)

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
                "model": (
                    self._options.model if self._options.model is not None else "gpt-4"
                ),
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
                # SSE format uses double newlines to separate events
                buffer = ""
                byte_buffer = b""
                async for chunk_bytes in response.content.iter_chunked(8192):
                    # Handle partial UTF-8 sequences at chunk boundaries
                    byte_buffer += chunk_bytes
                    try:
                        decoded_chunk = byte_buffer.decode("utf-8")
                        byte_buffer = b""  # Clear buffer on successful decode
                        buffer += decoded_chunk
                    except UnicodeDecodeError:
                        # Partial UTF-8 sequence at end, keep in byte_buffer for next chunk
                        if (
                            len(byte_buffer) > 4
                        ):  # UTF-8 max 4 bytes, if longer it's an error
                            # Try to decode as much as possible
                            decoded_chunk = byte_buffer.decode("utf-8", errors="ignore")
                            buffer += decoded_chunk
                            byte_buffer = b""
                        continue

                    # Process complete events (separated by double newlines)
                    while "\n\n" in buffer:
                        event, buffer = buffer.split("\n\n", 1)
                        event = event.strip()

                        if not event:
                            continue

                        # Skip SSE comment lines
                        if event.startswith(":"):
                            continue

                        # Parse SSE data (can be multi-line within a single event)
                        for line in event.splitlines():
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix

                                # Check for stream end
                                if data_str == "[DONE]":
                                    buffer = ""  # Clear buffer
                                    break

                                try:
                                    chunk = json.loads(data_str)
                                    # Convert Azure OpenAI format to SDK format
                                    message = self._convert_chunk_to_message(chunk)
                                    if message:
                                        yield message
                                except json.JSONDecodeError:
                                    logger.warning(
                                        "Failed to parse JSON chunk (invalid format)"
                                    )
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
            logger.error(f"HTTP error during Azure OpenAI request: {type(e).__name__}")
            raise AzureConnectionError("Azure OpenAI API error occurred") from e
        except Exception as e:
            logger.error(
                f"Unexpected error during Azure OpenAI request: {type(e).__name__}"
            )
            raise AzureConnectionError("Unexpected error occurred") from e

    def _prepare_messages(self) -> list[dict[str, Any]]:
        """Prepare messages array for Azure OpenAI API.

        Returns:
            List of message dictionaries in Azure OpenAI format
        """
        return [{"role": "user", "content": self._prompt}]

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
        content = delta.get("content")
        tool_calls = delta.get("tool_calls")

        # Return message if there's any content or tool calls
        # Note: In streaming mode, role is only present in the first chunk
        if content or tool_calls:
            # Get model from chunk or options with explicit None check
            model = chunk.get("model")
            if model is None:
                model = (
                    self._options.model if self._options.model is not None else "gpt-4"
                )

            message: dict[str, Any] = {
                "type": "assistant",
                "message": {
                    "content": [],
                    "model": model,
                },
            }

            # Add text content
            if content:
                message["message"]["content"].append({"type": "text", "text": content})

            # Add tool calls
            if tool_calls:
                for tool_call in tool_calls:
                    function = tool_call.get("function")
                    if not function:
                        logger.warning(
                            "Tool call missing 'function' field: %r", tool_call
                        )
                        continue

                    # Handle partial function arguments in streaming
                    arguments = function.get("arguments", "{}")
                    try:
                        parsed_args = json.loads(arguments) if arguments else {}
                    except json.JSONDecodeError:
                        # Arguments may be incomplete in streaming, skip for now
                        logger.debug(
                            "Skipping partial tool call arguments: %s", arguments
                        )
                        continue

                    message["message"]["content"].append(
                        {
                            "type": "tool_use",
                            "id": tool_call.get("id", ""),
                            "name": function.get("name", ""),
                            "input": parsed_args,
                        }
                    )

            return message

        return None

    def is_ready(self) -> bool:
        """Check if transport is ready for communication."""
        return self._ready
