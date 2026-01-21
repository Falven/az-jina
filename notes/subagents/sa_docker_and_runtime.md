# sa_docker_and_runtime (read-only emulation)

## Findings
- `az-reader/Dockerfile` builds runtime from `node:22`, installs Chrome, and runs `node build/stand-alone/crawl.js`.
- Reader search is expected to run with command `node build/stand-alone/search.js` (set in Terraform stack `20-workload`).
- `mcp-runtime/Dockerfile` builds `mcp-runtime` + `az-jina-mcp` with pnpm and runs `node mcp-runtime/dist/server.js`.
- `mcp-runtime/src/server.ts` rewrites fetch calls from `r.jina.ai` and `svip.jina.ai` to `MCP_READER_BASE`/`MCP_SEARCH_BASE`.
- MCP runtime expects env `JINA_API_KEY` (debug key) and `VITE_GHOST_API_KEY`.
- Current deploy script `ops/ops/deploy_workload_reader.py` builds from `reader-runtime/Dockerfile`, which conflicts with requirement to use `az-reader/Dockerfile`.
- `reader-runtime/` and `edge/` directories already exist; guardrails must ensure no new runtime wrappers.

## Exact contracts (runtime env)
- Reader container uses `PORT`, `NODE_OPTIONS`, and various crawler envs from `infra/terraform/stacks/20-workload`.
- MCP runtime env:
  - `MCP_READER_BASE` (rewrites `r.jina.ai`)
  - `MCP_SEARCH_BASE` (rewrites `svip.jina.ai` and `s.jina.ai`)
  - `JINA_API_KEY` (optional fallback bearer token)
  - `VITE_GHOST_API_KEY` (Jina blog search)

## Minimal patch (proposal)
```diff
diff --git a/ops/ops/deploy_workload_reader.py b/ops/ops/deploy_workload_reader.py
index 7b48f2e..aaaaaaa 100644
--- a/ops/ops/deploy_workload_reader.py
+++ b/ops/ops/deploy_workload_reader.py
@@ -36,12 +36,11 @@ def deploy_workload(
     build_and_push(
         env=env,
         target="az-reader",
-        dockerfile=Path("reader-runtime/Dockerfile"),
+        dockerfile=Path("az-reader/Dockerfile"),
         build_context=Path("."),
         include_paths=[
             Path("acr-build.yaml"),
-            Path("reader-runtime/Dockerfile"),
             Path("az-reader/Dockerfile"),
             Path("az-reader/package.json"),
             Path("az-reader/package-lock.json"),
```

## Verification commands
- `docker build -f az-reader/Dockerfile -t az-reader-local .`
- `docker build -f mcp-runtime/Dockerfile -t az-jina-mcp-local .`
- `pnpm --filter az-jina-mcp-runtime... install`
- `pnpm --filter az-jina-mcp-runtime run build`

## Parity risks
- Switching to `az-reader/Dockerfile` requires removing `reader-runtime` usage in ops scripts and guardrails.
- MCP runtime needs `MCP_READER_BASE`/`MCP_SEARCH_BASE` set; otherwise it will call public Jina endpoints.
