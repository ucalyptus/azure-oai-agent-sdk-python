# Azure OpenAI Agent SDK for Python

Python SDK for Azure OpenAI with API Management (APIM) and enterprise-level authentication using OAuth2 client credentials flow.

## Features

- **Enterprise Authentication**: OAuth2 client credentials flow with Azure AD
- **APIM Integration**: Full support for Azure API Management subscription keys
- **Streaming Responses**: Real-time streaming of Azure OpenAI responses
- **Type Safety**: Fully typed with Python type hints
- **Async/Await**: Built on modern async Python with anyio

## Installation

```bash
pip install azure-openai-agent-sdk
```

**Prerequisites:**
- Python 3.10+
- Azure AD Application with client credentials
- Azure OpenAI APIM endpoint and subscription key

## Configuration

### Azure AD Setup

Before using this SDK, you need:

1. **Azure AD Tenant ID**: Your organization's Azure AD tenant identifier
2. **Application (Client) ID**: Registered application ID in Azure AD
3. **Client Secret**: Client secret value for the application
4. **APIM Endpoint**: Your Azure APIM endpoint URL (e.g., `https://your-apim.azure-api.net/openai`)
5. **APIM Subscription Key**: Subscription key for your APIM instance

### Environment Variables (Recommended)

Store sensitive credentials in environment variables:

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_APIM_ENDPOINT="https://your-apim.azure-api.net/openai"
export AZURE_APIM_SUBSCRIPTION_KEY="your-subscription-key"
```

## Quick Start

```python
import os
import anyio
from claude_agent_sdk import azure_query, AzureOpenAIOptions

async def main():
    # Configure Azure OpenAI options
    options = AzureOpenAIOptions(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
        endpoint=os.environ["AZURE_APIM_ENDPOINT"],
        apim_subscription_key=os.environ["AZURE_APIM_SUBSCRIPTION_KEY"],
        model="gpt-4"  # Your deployment name
    )

    # Query Azure OpenAI
    async for message in azure_query(
        prompt="What is the capital of France?",
        options=options
    ):
        print(message)

anyio.run(main)
```

## Basic Usage

### Simple Query

```python
from claude_agent_sdk import azure_query, AzureOpenAIOptions, AssistantMessage, TextBlock

options = AzureOpenAIOptions(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
    endpoint="https://your-apim.azure-api.net/openai",
    apim_subscription_key="your-subscription-key",
    model="gpt-4"
)

async for message in azure_query(
    prompt="Explain quantum computing in simple terms",
    options=options
):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text)
```

### Custom Model Parameters

```python
options = AzureOpenAIOptions(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
    endpoint="https://your-apim.azure-api.net/openai",
    apim_subscription_key="your-subscription-key",
    model="gpt-4-turbo",
    max_tokens=2048,
    temperature=0.7  # Control randomness (0.0-2.0)
)

async for message in azure_query(
    prompt="Generate a creative story about space exploration",
    options=options
):
    print(message)
```

### Working Directory

```python
from pathlib import Path

options = AzureOpenAIOptions(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
    endpoint="https://your-apim.azure-api.net/openai",
    apim_subscription_key="your-subscription-key",
    model="gpt-4",
    cwd="/path/to/project"  # or Path("/path/to/project")
)
```

## Configuration Reference

### AzureOpenAIOptions

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | `str` | Yes | Azure AD tenant ID |
| `client_id` | `str` | Yes | Application (client) ID |
| `client_secret` | `str` | Yes | Client secret value |
| `endpoint` | `str` | Yes | APIM endpoint URL |
| `apim_subscription_key` | `str` | Yes | APIM subscription key |
| `model` | `str` | No | Model deployment name (default: "gpt-4") |
| `max_tokens` | `int` | No | Maximum tokens in response (default: 4096) |
| `temperature` | `float` | No | Sampling temperature 0.0-2.0 (default: None) |
| `scope` | `str` | No | OAuth2 scope (default: Azure Cognitive Services scope) |
| `tools` | `list[dict]` | No | Function calling tools |
| `cwd` | `str\|Path` | No | Working directory for operations |

## Authentication Flow

The SDK uses OAuth2 client credentials flow:

1. **Token Request**: SDK requests access token from Azure AD using client credentials
2. **Token Caching**: Access token is cached and automatically refreshed before expiry
3. **API Request**: Each API request includes:
   - `Authorization: Bearer {access_token}` header
   - `Ocp-Apim-Subscription-Key: {subscription_key}` header
4. **Token Refresh**: Tokens are refreshed automatically with a 5-minute buffer

## Security Best Practices

### ✅ DO

- Store credentials in environment variables or Azure Key Vault
- Use Azure Managed Identity where possible
- Rotate client secrets regularly (every 90 days recommended)
- Restrict APIM subscription key access using IP filtering
- Use separate credentials for development and production
- Monitor authentication logs in Azure AD

### ❌ DON'T

- Hardcode credentials in source code
- Commit credentials to version control
- Share client secrets via email or messaging
- Use production credentials in development environments
- Log or print access tokens

## Error Handling

```python
from claude_agent_sdk import azure_query, AzureOpenAIOptions
from claude_agent_sdk import CLIConnectionError
import aiohttp

async def query_with_error_handling():
    options = AzureOpenAIOptions(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
        endpoint=os.environ["AZURE_APIM_ENDPOINT"],
        apim_subscription_key=os.environ["AZURE_APIM_SUBSCRIPTION_KEY"],
        model="gpt-4"
    )

    try:
        async for message in azure_query(
            prompt="Hello, Azure OpenAI!",
            options=options
        ):
            print(message)
    except CLIConnectionError as e:
        print(f"Connection error: {e}")
    except aiohttp.ClientError as e:
        print(f"HTTP error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Advanced Usage

### Custom OAuth2 Scope

```python
options = AzureOpenAIOptions(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
    endpoint="https://your-apim.azure-api.net/openai",
    apim_subscription_key="your-subscription-key",
    model="gpt-4",
    scope="api://your-custom-scope/.default"  # Custom scope
)
```

### Function Calling (Tools)

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

options = AzureOpenAIOptions(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
    endpoint="https://your-apim.azure-api.net/openai",
    apim_subscription_key="your-subscription-key",
    model="gpt-4",
    tools=tools
)
```

## Migration from Claude SDK

If you're migrating from the Claude Agent SDK:

**Before (Claude):**
```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    model="claude-sonnet-4",
    max_turns=10
)

async for message in query(prompt="Hello", options=options):
    print(message)
```

**After (Azure OpenAI):**
```python
from claude_agent_sdk import azure_query, AzureOpenAIOptions

options = AzureOpenAIOptions(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["AZURE_CLIENT_SECRET"],
    endpoint=os.environ["AZURE_APIM_ENDPOINT"],
    apim_subscription_key=os.environ["AZURE_APIM_SUBSCRIPTION_KEY"],
    model="gpt-4",
    max_tokens=4096
)

async for message in azure_query(prompt="Hello", options=options):
    print(message)
```

## Troubleshooting

### Authentication Errors

**Error: `Failed to acquire Azure AD token`**
- Verify `tenant_id`, `client_id`, and `client_secret` are correct
- Check if the application has necessary API permissions
- Ensure client secret hasn't expired

**Error: `401 Unauthorized`**
- Verify APIM subscription key is valid
- Check if the APIM subscription is active
- Ensure the OAuth2 scope is correct

### Connection Errors

**Error: `Failed to connect to Azure OpenAI`**
- Verify the APIM endpoint URL is correct
- Check network connectivity to Azure
- Verify firewall rules allow outbound HTTPS

### Model Errors

**Error: `Model not found`**
- Verify the deployment name matches your Azure OpenAI deployment
- Check if the deployment is in the same region as APIM

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: [Report issues here]
- Documentation: [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- Azure Support: Contact Azure support for infrastructure issues

## Architecture

```
┌─────────────────────────────────────────┐
│   Your Python Application              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│   Azure OpenAI Agent SDK                │
│   - azure_query()                        │
│   - AzureHTTPTransport                   │
│   - AzureADAuth                          │
└──────────────┬───────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌─────────────┐  ┌──────────────────┐
│  Azure AD   │  │  Azure APIM      │
│  OAuth2     │  │  Subscription    │
│  (Token)    │  │  Key Validation  │
└─────────────┘  └──────────┬───────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  Azure OpenAI        │
                 │  (GPT-4, etc.)       │
                 └──────────────────────┘
```

## Package Information

- **Package Name**: `azure-openai-agent-sdk`
- **Version**: 0.2.0
- **Python**: >=3.10
- **Dependencies**: anyio, aiohttp, typing_extensions, mcp
