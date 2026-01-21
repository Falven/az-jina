# Decisions

- 2026-01-21T16:32:52Z Initialized notes + run_and_log.sh; subagents unavailable in-session, emulating in notes/subagents/*.md.

- 2026-01-21T16:59:15Z Auth contract and parity docs derived from az-reader build/shared + az-jina-mcp tool schemas.

- 2026-01-21T17:17:48Z F02: populated az-reader/thinapps-shared/backend from build/shared JS; tests run via node --test against build output to avoid symlink path issues.

- 2026-01-21T18:10:20Z F02: shim buffer.SlowBuffer in tests to avoid Node 25 SlowBuffer removal during civkit/jsonwebtoken load.

- 2026-01-21T18:11:20Z F02: replaced private thinapps-shared submodule with local JS build output + minimal .d.ts shims; added tests for auth/env/errors; removed az-reader/.gitmodules and gitlink.
