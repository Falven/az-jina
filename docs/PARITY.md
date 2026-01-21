# Parity Spec: Jina Reader + Search + MCP

This document defines the external behavior we must match for Reader, Search, and MCP.

## Domains and base URLs

Use these placeholders in docs and commands:

- `MCP_BASE=https://${MCP_SUBDOMAIN}.${BASE_DOMAIN}` (or ACA default domain during smoke tests)
- `READER_BASE=https://${READER_SUBDOMAIN}.${BASE_DOMAIN}`
- `SEARCH_BASE=https://${SEARCH_SUBDOMAIN}.${BASE_DOMAIN}`

## Auth parity (external behavior)

- MCP tools: bearer token is read from `Authorization: Bearer <token>`.
- Missing/invalid token responses are MCP tool errors with:
  - `content: [{ type: "text", text: "<message>" }]`
  - `isError: true`
- Jina Reader public behavior:
  - Read endpoints can be used without a key (rate-limited).
  - Search endpoints require a key for actual search; unauthenticated index returns a note.
- Auth error semantics:
  - Missing key -> 401 (Reader search), MCP tool error message about setting API key.
  - Invalid key -> 401, message "Invalid API key..." (Reader) or "Authentication failed..." (MCP).
  - Quota -> 402, message about topping up.
  - Rate limit -> 429, message about upgrading.

## MCP parity

### Endpoints

- `GET /` returns `text/yaml` with server metadata, tool list, and filter help.
- `GET|POST /v1` primary MCP endpoint (Streamable HTTP).
- `GET|POST /sse` and `/sse/message` are aliases (back-compat).
- Unknown paths return `404 text/yaml` with keys: `error`, `message`, `available_endpoints`, `suggestion`.

### CORS

`Access-Control-Allow-Methods: GET, POST, DELETE, OPTIONS`  
`Access-Control-Allow-Headers: Content-Type, Accept, Authorization, mcp-session-id, MCP-Protocol-Version`  
`Access-Control-Expose-Headers: mcp-session-id`

### Tool filtering (query params)

`exclude_tools`, `exclude_tags`, `include_tools`, `include_tags`  
Precedence: `exclude_tools` > `exclude_tags` > `include_tools` > `include_tags`

### Tool list (must match)

`primer`, `show_api_key`, `read_url`, `capture_screenshot_url`, `guess_datetime_url`,  
`search_web`, `search_arxiv`, `search_ssrn`, `search_images`, `search_jina_blog`,  
`expand_query`, `parallel_search_web`, `parallel_search_arxiv`, `parallel_search_ssrn`, `parallel_read_url`,  
`sort_by_relevance`, `deduplicate_strings`, `deduplicate_images`, `extract_pdf`

### Tool schemas (args)

- `show_api_key`: `{}`
- `primer`: `{}`
- `guess_datetime_url`: `{ url: string }`
- `capture_screenshot_url`: `{ url: string, firstScreenOnly?: boolean, return_url?: boolean }`
- `read_url`: `{ url: string | string[], withAllLinks?: boolean, withAllImages?: boolean }`
- `parallel_read_url`: `{ urls: Array<{ url: string, withAllLinks?: boolean, withAllImages?: boolean }>, timeout?: number }`
- `search_web`: `{ query: string | string[], num?: number, tbs?: string, location?: string, gl?: string, hl?: string }`
- `search_arxiv`: `{ query: string | string[], num?: number, tbs?: string }`
- `search_ssrn`: `{ query: string | string[], num?: number, tbs?: string }`
- `search_images`: `{ query: string, return_url?: boolean, tbs?: string, location?: string, gl?: string, hl?: string }`
- `search_jina_blog`: `{ query: string | string[], num?: number, tbs?: string }`
- `expand_query`: `{ query: string }`
- `parallel_search_web`: `{ searches: Array<{ query: string, num?: number, tbs?: string, location?: string, gl?: string, hl?: string }>, timeout?: number }`
- `parallel_search_arxiv`: `{ searches: Array<{ query: string, num?: number, tbs?: string }>, timeout?: number }`
- `parallel_search_ssrn`: `{ searches: Array<{ query: string, num?: number, tbs?: string }>, timeout?: number }`
- `sort_by_relevance`: `{ query: string, documents: string[], top_n?: number }`
- `deduplicate_strings`: `{ strings: string[], k?: number }`
- `deduplicate_images`: `{ images: string[], k?: number }`
- `extract_pdf`: `{ id?: string, url?: string, max_edge?: number, type?: string }`

## Reader parity (r.jina.ai)

### URL style

- `GET ${READER_BASE}/https://example.com/path`
- `POST ${READER_BASE}/` with body `url=https://example.com/#/route` (SPA/hash routes)
  - `GET|POST ${READER_BASE}/::url` maps to the same crawl handler.

### Headers (public + MCP usage)

- `Accept: application/json` (JSON result)
- `Accept: text/event-stream` (SSE stream)
- `X-Cache-Tolerance`, `X-No-Cache`
- `X-Respond-With` (markdown|html|text|pageshot|screenshot|content|readerlm-v2|vlm)
- `X-Wait-For-Selector`, `X-Target-Selector`, `X-Remove-Selector`
- `X-Keep-Img-Data-Url`, `X-Proxy-Url`, `X-Proxy`, `X-Robots-Txt`
- `DNT`, `X-Set-Cookie`, `X-User-Agent`, `X-Timeout`, `X-Locale`, `X-Referer`, `X-Token-Budget`
- `X-With-Generated-Alt`, `X-With-Images-Summary`, `X-With-Links-Summary`
- `X-Retain-Images` (none|all|alt|all_p|alt_p)
- `X-With-Iframe`, `X-With-Shadow-Dom`
- `X-Return-Format: screenshot|pageshot` (screenshot tool use)

## Search parity (s.jina.ai)

### URL style

- `GET ${SEARCH_BASE}/your+query`
- In-site search: `GET ${SEARCH_BASE}/query?site=example.com&site=another.com`
- Index endpoint: `GET|POST ${SEARCH_BASE}/search`

### JSON mode

- `Accept: application/json` returns list of results with `title`, `url`, `content`.

## Concrete test commands (to run later)

### MCP

```bash
curl -sS "${MCP_BASE}/" | head -n 20
curl -sS "${MCP_BASE}/v1?exclude_tags=parallel" -H "Authorization: Bearer ${AZ_JINA_API_KEY}"
```

### Reader

```bash
curl -sS "${READER_BASE}/https://example.com"
curl -sS "${READER_BASE}/https://example.com" -H "Accept: application/json"
```

### Search

```bash
curl -sS "${SEARCH_BASE}/jina+ai?site=jina.ai" -H "Authorization: Bearer ${AZ_JINA_API_KEY}"
curl -sS "${SEARCH_BASE}/jina+ai?site=jina.ai" -H "Accept: application/json" -H "Authorization: Bearer ${AZ_JINA_API_KEY}"
```
