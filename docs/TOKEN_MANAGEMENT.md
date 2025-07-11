# Token Management Guide

This guide explains how to generate and manage JWT tokens for your Invoice Parser API clients.

## Quick Start

The token generation script uses `uv` to manage its dependencies so you must install it first. Follow the instructions 
on the [`uv` documentation page](https://docs.astral.sh/uv/getting-started/installation/) and come back once you are done.

Once installed, you should also install an uv-managed python interpreter. The easiest way to achieve this is by running

```bash
$ uv python install
```

Once installed, make sure you have the `SECRET_KEY` environment variable adequately set and that it has the same value 
as the machine in which the production API container is running (otherwise the API won't be able to authenticate your 
generated tokens because the keys won't match)

Now you should be ready to generate some tokens. The CLI is pretty self-explanatory but here are some useful examples:

**Generate token for a single client (valid for 1 year)**
```bash
$ ./scripts/tokens.py generate --username "client@company.com" --days 365
```

## Understanding the Token Generator

The token generator script is a command-line utility that helps you create and manage JWT tokens for API access. It 
provides two main commands: `generate` for creating new tokens and `verify` for checking existing ones.

When you run the script without any arguments, you'll see the available commands:

```bash
$ ./scripts/tokens.py --help
```

## Generating Tokens

The `generate` command creates JWT tokens with customizable parameters. The most common use case is creating a token for
a client that needs to access your API.

To generate a basic token valid for 30 days (the default), run:

```bash
$ ./scripts/tokens.py generate --username "client@example.com"
```

You can customize the validity period using the `--days` parameter. For example, to create a token valid for one year:

```bash
$ ./scripts/tokens.py generate --username "client@company.com" --days 365
```

The script also supports role-based access control. You can assign either a "user" or "admin" role to tokens:

```bash
$ ./scripts/tokens.py generate --username "admin@company.com" --role admin --days 90
```

## Output Formats

The token generator provides three different output formats to suit your needs.

The default "full" format displays the token along with helpful details:

```bash
$ ./scripts/tokens.py generate --username "client@example.com" --days 30
```

This will show the token in cyan color, followed by details about the username, role, expiration, and creation time.

If you need just the token itself (useful for scripting or piping to other commands), use the "token" format:

```bash
$ ./scripts/tokens.py generate --username "client@example.com" --output token
```

For programmatic integration, the "json" format provides structured data:

```bash
$ ./scripts/tokens.py generate --username "client@example.com" --output json
```

This returns a JSON object containing the token, username, role, expiration details, and timestamps.

## Verifying Tokens

The `verify` command allows you to check if a token is valid and see its contents. This is particularly useful when 
debugging authentication issues or checking token expiration.

To verify a token, run:

```bash
$ ./scripts/tokens.py verify "your-jwt-token-here"
```

The verification process will tell you if the token is valid, show the encoded username and role, display when it was 
issued and when it expires, and calculate how much time remains before expiration.

If a token has expired or is invalid, the script will display an appropriate error message.

## Secret Key Management

The security of your JWT tokens depends entirely on keeping your secret key safe. The token generator looks for the 
secret key in the following order: the `--secret-key` command-line option (if provided), the `SECRET_KEY` environment 
variable, or the `.env` file in your project root.

To set up your secret key, first generate a secure random key:

```bash
$ openssl rand -hex 32
```

Then add it to your `.env` file:

```
SECRET_KEY=your-generated-secret-key-here
```

Remember that the secret key used to generate tokens must match the one used by your API server. If they don't match, 
the API will reject all tokens as invalid.

## Using Tokens with the API

Once you have generated a token, clients can use it to authenticate with your API. The Invoice Parser API expects the 
JWT token in the Authorization header.

Here's how to use the token with curl:

```bash
$ curl -X POST http://localhost:8000/parse \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "invoice=@/path/to/invoice.pdf"
```

For Python clients, you might create a simple wrapper:

```python
import requests

class InvoiceParserClient:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def parse_invoice(self, pdf_path):
        with open(pdf_path, 'rb') as f:
            response = requests.post(
                f"{self.api_url}/parse",
                headers=self.headers,
                files={'invoice': f}
            )
        return response.json()

# Usage
client = InvoiceParserClient("http://localhost:8000", "your-token-here")
result = client.parse_invoice("invoice.pdf")
```

## Best Practices

When managing tokens for production use, consider these recommendations.

Set appropriate expiration times based on your use case. For development and testing, 7-30 days is usually sufficient. 
For regular clients, 90-180 days provides a good balance. For trusted partners or internal systems, you might use 365 
days.

Create separate tokens for each client or system that needs access. This allows you to revoke access for individual 
clients without affecting others, track usage per client, and apply different expiration times or roles as needed.

Keep a record of issued tokens in a secure location. While you cannot retrieve the original token later (for security 
reasons), you should track which clients have active tokens, when tokens were issued and when they expire, and any 
special permissions or limitations.

Plan for token rotation before they expire. Contact clients well in advance, generate new tokens with sufficient overlap
time, and consider implementing a grace period where both old and new tokens work.

## Troubleshooting

If you encounter the error "Please set the SECRET_KEY environment variable", ensure you have created a `.env` file with 
the SECRET_KEY, or set the environment variable directly, or provide it via the `--secret-key` option.

When seeing "Token has expired" errors, generate a new token for the affected client. Consider implementing automated 
alerts for tokens nearing expiration.

If tokens are reported as invalid, verify that the secret key matches between token generation and API server, the token
is being transmitted correctly without truncation, and there are no extra spaces or newlines in the token string.

## Advanced Usage

For automation scenarios, you can integrate token generation into your deployment scripts:

```bash
#!/bin/bash
# generate-client-tokens.sh

# Read client list and generate tokens
while IFS= read -r email; do
    token=$(./scripts/tokens.py generate --username "$email" --days 365 --output token)
    echo "$email,$token" >> client_tokens.csv
done < clients.txt
```

To programmatically check token expiration:

```python
#!/usr/bin/env python3
import subprocess


# Get token info in JSON format
result = subprocess.run(
    ['./scripts/tokens.py', 'verify', 'your-token'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    # Token is valid, parse the output to get expiration
    # (Note: actual verify command outputs text, not JSON)
    print("Token is valid")
else:
    print("Token is invalid or expired")
```