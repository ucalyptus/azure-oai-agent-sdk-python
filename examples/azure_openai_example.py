"""Example usage of Azure OpenAI Agent SDK with enterprise authentication.

This example demonstrates how to use the Azure OpenAI Agent SDK with:
- OAuth2 client credentials flow
- Azure API Management (APIM) subscription keys
- Streaming responses
"""

import os

import aiohttp
import anyio

from claude_agent_sdk import (
    AssistantMessage,
    AzureOpenAIOptions,
    CLIConnectionError,
    TextBlock,
    azure_query,
)


async def basic_query():
    """Basic query example with Azure OpenAI."""
    print("=== Basic Query Example ===\n")

    # Configure Azure OpenAI options
    # IMPORTANT: Store these values in environment variables, not hardcoded!
    options = AzureOpenAIOptions(
        tenant_id=os.environ.get("AZURE_TENANT_ID", "your-tenant-id"),
        client_id=os.environ.get("AZURE_CLIENT_ID", "your-client-id"),
        client_secret=os.environ.get("AZURE_CLIENT_SECRET", "your-client-secret"),
        endpoint=os.environ.get(
            "AZURE_APIM_ENDPOINT", "https://your-apim.azure-api.net/openai"
        ),
        apim_subscription_key=os.environ.get(
            "AZURE_APIM_SUBSCRIPTION_KEY", "your-subscription-key"
        ),
        model="gpt-4",  # Your deployment name
    )

    # Query Azure OpenAI
    async for message in azure_query(
        prompt="What is the capital of France? Please answer in one sentence.",
        options=options,
    ):
        # Print all messages
        print(f"Message type: {type(message).__name__}")

        # Extract and print text content from assistant messages
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Response: {block.text}")


async def custom_parameters_example():
    """Example with custom model parameters."""
    print("\n=== Custom Parameters Example ===\n")

    options = AzureOpenAIOptions(
        tenant_id=os.environ.get("AZURE_TENANT_ID", "your-tenant-id"),
        client_id=os.environ.get("AZURE_CLIENT_ID", "your-client-id"),
        client_secret=os.environ.get("AZURE_CLIENT_SECRET", "your-client-secret"),
        endpoint=os.environ.get(
            "AZURE_APIM_ENDPOINT", "https://your-apim.azure-api.net/openai"
        ),
        apim_subscription_key=os.environ.get(
            "AZURE_APIM_SUBSCRIPTION_KEY", "your-subscription-key"
        ),
        model="gpt-4-turbo",
        max_tokens=2048,
        temperature=0.7,  # More creative responses
    )

    async for message in azure_query(
        prompt="Write a haiku about artificial intelligence.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Response:\n{block.text}\n")


async def error_handling_example():
    """Example with error handling."""
    print("\n=== Error Handling Example ===\n")

    options = AzureOpenAIOptions(
        tenant_id=os.environ.get("AZURE_TENANT_ID", "your-tenant-id"),
        client_id=os.environ.get("AZURE_CLIENT_ID", "your-client-id"),
        client_secret=os.environ.get("AZURE_CLIENT_SECRET", "your-client-secret"),
        endpoint=os.environ.get(
            "AZURE_APIM_ENDPOINT", "https://your-apim.azure-api.net/openai"
        ),
        apim_subscription_key=os.environ.get(
            "AZURE_APIM_SUBSCRIPTION_KEY", "your-subscription-key"
        ),
        model="gpt-4",
    )

    try:
        async for message in azure_query(
            prompt="Hello, Azure OpenAI!",
            options=options,
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Response: {block.text}")

    except CLIConnectionError as e:
        print(f"Connection error: {e}")
        print("Check your Azure AD credentials and APIM configuration.")

    except aiohttp.ClientError as e:
        print(f"HTTP error: {e}")
        print("Check your network connectivity and APIM endpoint.")

    except Exception as e:
        print(f"Unexpected error: {e}")


async def check_environment():
    """Check if environment variables are set."""
    required_vars = [
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_APIM_ENDPOINT",
        "AZURE_APIM_SUBSCRIPTION_KEY",
    ]

    missing = [var for var in required_vars if not os.environ.get(var)]

    if missing:
        print("⚠️  Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nPlease set these environment variables before running the examples:")
        print('export AZURE_TENANT_ID="your-tenant-id"')
        print('export AZURE_CLIENT_ID="your-client-id"')
        print('export AZURE_CLIENT_SECRET="your-client-secret"')
        print('export AZURE_APIM_ENDPOINT="https://your-apim.azure-api.net/openai"')
        print('export AZURE_APIM_SUBSCRIPTION_KEY="your-subscription-key"')
        print("\n" + "=" * 60)
        return False

    print("✓ All required environment variables are set!\n")
    print("=" * 60)
    return True


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Azure OpenAI Agent SDK - Example Usage")
    print("=" * 60 + "\n")

    # Check environment
    if not await check_environment():
        print("\nRunning examples with placeholder credentials (will fail)...")
        print("Set environment variables to test with real Azure OpenAI.\n")

    # Run examples
    try:
        await basic_query()
        await custom_parameters_example()
        await error_handling_example()
    except Exception as e:
        print(f"\nExample failed: {e}")
        print("\nThis is expected if you haven't configured Azure credentials.")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    anyio.run(main)
