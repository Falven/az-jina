# sa_auth_contract (read-only emulation)

## Findings
- Reader auth is enforced via `JinaEmbeddingsAuthDTO` in `az-reader/src/dto/jina-embeddings-auth.ts` (reads `Authorization: Bearer <token>` or `_token` input).
- The dashboard client is defined in `az-reader/build/shared/3rd-party/jina-embeddings.js` (base URL `https://api.jina.ai/dashboard`).
- Auth client POSTs to `/authorization` (fallback `/auth/authorization`) with JSON `{ token }`.
- Token validation POSTs to `/validate` (fallback `/authorization`, `/auth/validate`) with JSON `{ token }`.
- Usage reporting POSTs to `/usage` (fallback `/reportUsage`, `/usage/report`) with JSON `{ token, ...usagePayload }`.
- Dashboard requests include `Authorization: Bearer <dashboard_api_key>` plus `Accept`/`Content-Type: application/json`.
- On 401 from dashboard, Reader throws `AuthenticationFailedError` with message "Invalid API key, please get a new one from https://jina.ai".
- Missing token triggers `AuthenticationRequiredError` with message "Jina API key is required to authenticate. Please get one from https://jina.ai".
- `build/shared/enforce-auth.js` overrides `getBrief` to validate structured tokens against Key Vault (prefix/keyId/secret).
- MCP tool errors map HTTP 401/402/429 to auth/quota/rate-limit messages (`az-jina-mcp/src/utils/api-error-handler.ts`).

## Exact contracts
- Base URL: `https://api.jina.ai/dashboard` (overrideable in client constructor).
- `POST /authorization` (or `/auth/authorization`)
  - Headers: `Authorization: Bearer <dashboard_api_key>`, `Content-Type: application/json`, `Accept: application/json`
  - Body: `{ "token": "<user_api_key>" }`
  - Response: `{ "data": { "user_id": string, "full_name": string, "wallet": { "total_balance": number, "total_used"?: number }, "metadata"?: object, "customRateLimits"?: { [tag]: Array<{ occurrence: number, periodSeconds: number, effectiveFrom?: string, expiresAt?: string }> } } }`
- `POST /validate` (fallback `/authorization`, `/auth/validate`)
  - Same headers/body; response normalized as above.
- `POST /usage` (fallback `/reportUsage`, `/usage/report`)
  - Body: `{ token, model_name, api_endpoint, consumer: { id, user_id }, usage: { total_tokens }, labels: { model_name } }`
- Error semantics
  - Missing token -> HTTP 401 -> Reader raises AuthenticationRequiredError with message above.
  - Invalid token -> HTTP 401 -> Reader raises AuthenticationFailedError with message above.
  - Quota exceeded -> HTTP 402 (MCP clients map to "out of quota" message).
  - Rate limit -> HTTP 429 (MCP clients map to "rate limit exceeded" message).
- Self-host env knobs (from `build/shared/enforce-auth.js`): `API_KEY_PREFIX`, `API_KEY_CACHE_TTL_SECONDS`, `KEY_VAULT_URI` or `SELF_HOST_TOKENS_VAULT_URL`, `AZURE_CLIENT_ID`, `ALLOW_ANONYMOUS`.

## Minimal patch (proposal)
```diff
diff --git a/docs/AUTH_CONTRACT.md b/docs/AUTH_CONTRACT.md
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/docs/AUTH_CONTRACT.md
@@
++# Auth contract (Reader/MCP)
++Base URL: https://api.jina.ai/dashboard
++POST /authorization | /auth/authorization
++POST /validate | /authorization | /auth/validate
++POST /usage | /reportUsage | /usage/report
++Headers: Authorization: Bearer <dashboard_api_key>
++Body: { token, ... }
++Response: { data: { user_id, full_name, wallet, metadata?, customRateLimits? } }
++Errors: 401 missing/invalid, 402 quota, 429 rate limit
```

## Verification commands
- `curl -sS -X POST "https://api.jina.ai/dashboard/authorization" -H "Authorization: Bearer $DASHBOARD_KEY" -H "Content-Type: application/json" -d '{"token":"$USER_KEY"}'`
- `curl -sS -X POST "https://api.jina.ai/dashboard/validate" -H "Authorization: Bearer $DASHBOARD_KEY" -H "Content-Type: application/json" -d '{"token":"$USER_KEY"}'`
- `curl -sS -X POST "https://api.jina.ai/dashboard/usage" -H "Authorization: Bearer $DASHBOARD_KEY" -H "Content-Type: application/json" -d '{"token":"$USER_KEY","model_name":"reader-crawl","api_endpoint":"/","consumer":{"id":"u","user_id":"u"},"usage":{"total_tokens":1},"labels":{"model_name":"reader-crawl"}}'`

## Parity risks
- The civkit `AuthenticationRequiredError`/`AuthenticationFailedError` to HTTP status mapping is in dependency code; verify exact status/code path.
- `customRateLimits` schema normalization may differ if auth service omits fields or returns non-object values.
- Dashboard stub behavior (no server API key -> fake user) may be relied on in tests; decide if custom auth should emulate.
- `authorization` vs `validate` behavior divergence is unknown; Jina may apply different policies.
