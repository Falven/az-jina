# Auth Contract (Reader + MCP)

This document defines the auth API contract that Reader and MCP rely on.

## Dashboard auth API (Reader -> auth service)

Base URL (default): `https://api.jina.ai/dashboard`

All endpoints are `POST` and require:

- `Authorization: Bearer <dashboard_api_key>`
- `Content-Type: application/json`
- `Accept: application/json`

### Endpoints

- `/authorization` (fallback: `/auth/authorization`)
- `/validate` (fallback: `/authorization`, `/auth/validate`)
- `/usage` (fallback: `/reportUsage`, `/usage/report`)

### Request bodies

Authorization / Validate:

```json
{
  "token": "<user_api_key>"
}
```

Usage report:

```json
{
  "token": "<user_api_key>",
  "model_name": "reader-crawl",
  "api_endpoint": "/",
  "consumer": { "id": "user_id", "user_id": "user_id" },
  "usage": { "total_tokens": 123 },
  "labels": { "model_name": "reader-crawl" }
}
```

### Response schema (required fields)

```json
{
  "data": {
    "user_id": "string",
    "full_name": "string",
    "wallet": { "total_balance": 1234, "total_used": 0 },
    "metadata": { "speed_level": "string" },
    "customRateLimits": {
      "SEARCH": [
        { "occurrence": 100, "periodSeconds": 60, "effectiveFrom": "2024-01-01T00:00:00Z" }
      ]
    }
  }
}
```

Notes:
- `metadata` and `customRateLimits` are optional but should be objects when present.
- `customRateLimits` values are arrays of objects with `occurrence` and `periodSeconds`.

## Error semantics

Reader behavior is driven by auth status codes and local errors:

- Missing API key: Reader raises `AuthenticationRequiredError` before calling auth service.
- Invalid API key: auth service returns `401`, Reader raises `AuthenticationFailedError`.
- Quota exhausted: auth service returns `402`.
- Rate limit: auth service returns `429`.

MCP tool error mapping expects:

- `401` -> "Authentication failed. Please set your API key in the Jina AI MCP settings."
- `402` -> "This key is out of quota. Please top up this key at https://jina.ai"
- `429` -> "Rate limit exceeded. Please upgrade your API key..."

## Self-host token format (Key Vault)

When using Key Vault-backed tokens (self-host mode), tokens are structured:

```
<prefix>_<keyId>_<secret>
```

- `prefix` default: `azjina` (env: `API_KEY_PREFIX`)
- `keyId` regex: `[a-zA-Z0-9-]{6,64}`
- Secret name in Key Vault: `{prefix}-api-key-{keyId}`

Related env vars (Reader auth enforcement):

- `KEY_VAULT_URI` or `SELF_HOST_TOKENS_VAULT_URL`
- `AZURE_CLIENT_ID` (managed identity client ID)
- `API_KEY_CACHE_TTL_SECONDS`
- `ALLOW_ANONYMOUS`
