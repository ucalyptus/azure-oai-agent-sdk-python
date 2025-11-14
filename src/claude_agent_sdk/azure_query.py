"""Query function for Azure OpenAI APIM interactions."""

from collections.abc import AsyncIterator

from ._internal.message_parser import parse_message
from ._internal.transport.azure_http import AzureHTTPTransport
from .types import AzureOpenAIOptions, Message


async def azure_query(
    *,
    prompt: str,
    options: AzureOpenAIOptions,
) -> AsyncIterator[Message]:
    """Query Azure OpenAI APIM with enterprise authentication.

    This function provides direct access to Azure OpenAI through API Management (APIM)
    with OAuth2 client credentials flow for enterprise-level authentication.

    Args:
        prompt: The prompt string to send to Azure OpenAI.
        options: Azure OpenAI configuration with:
                 - tenant_id: Azure AD tenant ID
                 - client_id: Application (client) ID
                 - client_secret: Client secret value
                 - endpoint: APIM endpoint URL
                 - apim_subscription_key: APIM subscription key
                 - model: Deployment name (default: "gpt-4")

    Yields:
        Messages from the Azure OpenAI response

    Example - Simple query:
        ```python
        from claude_agent_sdk import azure_query, AzureOpenAIOptions

        options = AzureOpenAIOptions(
            tenant_id="your-tenant-id",
            client_id="your-client-id",
            client_secret="your-client-secret",
            endpoint="https://your-apim.azure-api.net/openai",
            apim_subscription_key="your-subscription-key",
            model="gpt-4"
        )

        async for message in azure_query(
            prompt="What is the capital of France?",
            options=options
        ):
            if hasattr(message, 'content'):
                print(message.content)
        ```

    Example - With custom parameters:
        ```python
        options = AzureOpenAIOptions(
            tenant_id="your-tenant-id",
            client_id="your-client-id",
            client_secret="your-client-secret",
            endpoint="https://your-apim.azure-api.net/openai",
            apim_subscription_key="your-subscription-key",
            model="gpt-4-turbo",
            max_tokens=2048,
            temperature=0.7
        )

        async for message in azure_query(
            prompt="Generate a Python function to sort a list",
            options=options
        ):
            print(message)
        ```

    Security Notes:
        - Never hardcode credentials in your source code
        - Use environment variables or Azure Key Vault for secrets
        - Rotate client secrets regularly
        - Restrict APIM subscription key access
    """
    transport = AzureHTTPTransport(prompt, options)

    try:
        # Connect to Azure OpenAI
        await transport.connect()

        # Stream messages from Azure OpenAI
        async for raw_message in transport.read_messages():
            # Parse the message into typed format
            message = parse_message(raw_message)
            yield message

    finally:
        # Clean up connection
        await transport.close()
