# sa_thinapps_shared_reverse_engineer (read-only emulation)

## Findings
- `az-reader/src/shared` is a symlink to `../thinapps-shared/backend`, but `az-reader/thinapps-shared` is empty.
- `az-reader/src` imports many modules from `../shared/*` (services, db, lib, utils, 3rd-party).
- Compiled output already contains `az-reader/build/shared/*` with full JS implementations (likely the missing thinapps-shared).
- `build/shared` includes `3rd-party`, `db`, `lib`, `services`, and `utils` subtrees plus `index.js` and `enforce-auth.js`.
- `build/shared/index.js` re-exports decorators and shared services (Logger, TempFileManager, FirebaseStorageBucketControl, etc).
- Several shared modules are thin re-exports of existing `az-reader/src/services/*` (e.g., `shared/services/async-context`).
- Auth-related shared modules are in build output (`3rd-party/jina-embeddings`, `db/jina-embeddings-token-account`, `services/secrets`).
- Rate limiting and persistence are implemented in `build/shared/services/rate-limit.js` and `build/shared/lib/firestore.js` (Cosmos-backed).
- Azure helpers are in `build/shared/services/azure-config.js` and `build/shared/services/blob-storage.js`.
- `build/shared/enforce-auth.js` contains Key Vault-backed token validation override, but it is not wired in infra (NODE_OPTIONS empty).

## Exact contracts (modules + key exports)
- `shared/index` -> `CloudHTTPv2`, `CloudTaskV2`, `Param`, `Ctx`, `RPCReflect`, `Logger`, `TempFileManager`, `FirebaseStorageBucketControl`, `ServiceBadAttemptError`.
- `shared/services/secrets` -> `SecretExposer` class + default instance; reads env for `SERPER_SEARCH_API_KEY`, `BRAVE_SEARCH_API_KEY`, `CLOUD_FLARE_API_KEY`, `JINA_EMBEDDINGS_DASHBOARD_API_KEY`, `JINA_SERP_API_KEY`.
- `shared/3rd-party/jina-embeddings` -> `JinaEmbeddingsDashboardHTTP` with `authorization`, `validateToken`, `reportUsage`.
- `shared/db/jina-embeddings-token-account` -> `JinaEmbeddingsTokenAccount` (wallet, metadata, customRateLimits).
- `shared/services/rate-limit` -> `RateLimitControl`, `RateLimitDesc`, `RateLimitTriggeredError`.
- `shared/lib/firestore` -> `FirestoreRecord`, `FirestoreQuery`, `Timestamp` (Cosmos-backed persistence).
- `shared/3rd-party/serper-search` -> `Serper*` HTTP clients + `WORLD_COUNTRIES`, `WORLD_LANGUAGES`.
- `shared/3rd-party/brave-search` / `shared/3rd-party/brave-types` -> Brave search client + header options.
- `shared/3rd-party/internal-serp` -> `JinaSerpApiHTTP`.
- `shared/services/proxy-provider` -> `ProxyProviderService` (PROXY_POOL/HTTP_PROXY env).
- `shared/utils/openai` -> `countGPTToken`.
- `shared/utils/audition` -> `getAuditionMiddleware`.
- `shared/services/common-llm` -> `LLMManager` (Azure OpenAI).
- `shared/services/common-iminterrogate` -> `ImageInterrogationManager`.
- `shared/services/firebase-storage-bucket` -> `FirebaseStorageBucketControl` (Blob storage adapter).

## Minimal patch (proposal)
```diff
diff --git a/az-reader/thinapps-shared/backend/index.ts b/az-reader/thinapps-shared/backend/index.ts
new file mode 100644
index 0000000..2222222
--- /dev/null
+++ b/az-reader/thinapps-shared/backend/index.ts
@@
+export * from "../../build/shared/index.js";
```
```diff
diff --git a/az-reader/thinapps-shared/backend/services/secrets.ts b/az-reader/thinapps-shared/backend/services/secrets.ts
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/az-reader/thinapps-shared/backend/services/secrets.ts
@@
+export { default } from "../../../build/shared/services/secrets.js";
+export * from "../../../build/shared/services/secrets.js";
```
```diff
diff --git a/scripts/bootstrap_thinapps_shared.sh b/scripts/bootstrap_thinapps_shared.sh
new file mode 100755
index 0000000..4444444
--- /dev/null
+++ b/scripts/bootstrap_thinapps_shared.sh
@@
+#!/usr/bin/env bash
+set -euo pipefail
+mkdir -p az-reader/thinapps-shared/backend
+cp -R az-reader/build/shared/* az-reader/thinapps-shared/backend/
```

## Verification commands
- `node -e "require('./az-reader/build/shared/3rd-party/jina-embeddings.js')"`
- `node -e "require('./az-reader/build/shared/services/secrets.js')"`
- `node -e "require('./az-reader/build/shared/services/rate-limit.js')"`
- `node -e "require('./az-reader/build/shared/lib/firestore.js')"`
- `npm --prefix az-reader run dry-run`

## Parity risks
- Directly re-exporting build output may hide TypeScript types; tests may need TS shims.
- Some shared modules depend on Azure services (Cosmos/Blob/OpenAI) and require env; tests may need stubs.
- `enforce-auth` is present in build output but not wired; parity depends on whether we load it via NODE_OPTIONS.
