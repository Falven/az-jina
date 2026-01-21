# Decisions

- 2026-01-21T16:32:52Z Initialized notes + run_and_log.sh; subagents unavailable in-session, emulating in notes/subagents/*.md.

- 2026-01-21T16:59:15Z Auth contract and parity docs derived from az-reader build/shared + az-jina-mcp tool schemas.

- 2026-01-21T17:17:48Z F02: populated az-reader/thinapps-shared/backend from build/shared JS; tests run via node --test against build output to avoid symlink path issues.

- 2026-01-21T18:10:20Z F02: shim buffer.SlowBuffer in tests to avoid Node 25 SlowBuffer removal during civkit/jsonwebtoken load.

- 2026-01-21T18:11:20Z F02: replaced private thinapps-shared submodule with local JS build output + minimal .d.ts shims; added tests for auth/env/errors; removed az-reader/.gitmodules and gitlink.

- 2026-01-21T18:36:10Z F03: added FastAPI auth service in services/auth using Key Vault + managed identity; added Dockerfile and contract test script.
- 2026-01-21T18:36:10Z F03: root uv workspace (pyproject.toml + uv.lock) so  works; ops.keys list no longer emits secrets.

- 2026-01-21T18:36:10Z F03: added FastAPI auth service in services/auth using Key Vault + managed identity; added Dockerfile and contract test script.
- 2026-01-21T18:36:10Z F03: root uv workspace (pyproject.toml + uv.lock) so uv run python -m ops.keys works; ops.keys list no longer emits secrets.

- 2026-01-21T18:56:05Z F04: added JINA_EMBEDDINGS_DASHBOARD_BASE_URL env override in az-reader thinapps-shared secrets and auth DTO to point at custom auth service.

- 2026-01-21T19:04:30Z F05: added 23-workload-auth stack and deploy hook; deploy_workload now skips edge and updates reader auth_dashboard_base_url after auth deploy; deploy_workload_reader uses az-reader/Dockerfile.

- 2026-01-21T19:06:40Z Removed edge and reader-runtime folders (and 22-workload-edge stack dir) to satisfy no-edge/no-runtime guardrails.

- 2026-01-21T20:21:50Z az-reader thinapps-shared now lazy-loads Azure SDKs so COSMOS/BLOB can remain optional without adding dependencies or changing the Dockerfile.

- 2026-01-21T20:36:49Z Fixed SnapshotFormatter threadLocal injection by using AsyncLocalContext class; updated build/shared snapshot-formatter output to match (build/ is gitignored).

- 2026-01-21T20:45:13Z Terraform: avoid sensitive maps in Key Vault secret for_each by iterating over non-sensitive key sets (stacks 20/21/23).
