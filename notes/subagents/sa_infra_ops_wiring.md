# sa_infra_ops_wiring (read-only emulation)

## Findings
- Terraform stacks exist for bootstrap (`00-bootstrap`), reader/search (`20-workload`), MCP (`21-workload-mcp`), and edge (`22-workload-edge`).
- `ops/ops/deploy_workload_reader.py` deploys stack 20; `ops/ops/deploy_workload.py` deploys stack 21 and also edge (stack 22).
- Stack 20 provisions Key Vault (optional) and injects `SELF_HOST_TOKENS_SECRET_NAME` + `SELF_HOST_TOKENS_VAULT_URL` into app settings.
- Stack 21 reads reader state outputs and injects `MCP_READER_BASE`/`MCP_SEARCH_BASE` into MCP runtime.
- Key Vault secret overrides are supported via `secret_environment_overrides` in stacks 20/21.
- `ops/ops/keys.py` manages API key secrets in Key Vault with names `prefix-api-key-<keyId>`.
- `ops/ops/manage_tokens.py` manages a legacy list in `self-host-tokens` secret.
- `22-workload-edge` is an ingress layer (explicitly disallowed by requirements).

## Exact contracts (infra/env)
- Stack 20 app settings (reader/search): `PORT`, `NODE_OPTIONS`, `SELF_HOST_TOKENS_SECRET_NAME`, `SELF_HOST_TOKENS_VAULT_URL`, plus `app_settings` map.
- Stack 21 app settings (MCP): `PORT`, `MCP_READER_BASE`, `MCP_SEARCH_BASE`, plus `app_settings` map.
- Key Vault integration via `secret_environment_overrides` maps env var -> secret name; secrets can be seeded via `secrets` map.
- Container Apps created via modules `modules/aca/app` and `modules/aca/reader-app` with user-assigned identity and optional Key Vault secret refs.

## Minimal patch (proposal)
```diff
diff --git a/ops/ops/deploy_workload.py b/ops/ops/deploy_workload.py
index 3d4ad6e..bbbbbbb 100644
--- a/ops/ops/deploy_workload.py
+++ b/ops/ops/deploy_workload.py
@@ -61,6 +61,7 @@ def deploy_workload(
     terraform_apply(paths_mcp.workload, tfvars_mcp, True, extra)
     _log_app_endpoints(paths_mcp.workload)
-    # skip edge deployment (edge stack disallowed)
+    return
```
```diff
diff --git a/infra/terraform/stacks/23-workload-auth/main.tf b/infra/terraform/stacks/23-workload-auth/main.tf
new file mode 100644
index 0000000..5555555
--- /dev/null
+++ b/infra/terraform/stacks/23-workload-auth/main.tf
@@
+// New auth service Container App using modules/aca/app with Key Vault + managed identity
```

## Verification commands
- `uv run python -m ops.deploy_bootstrap ${ENV}`
- `uv run python -m ops.deploy_workload_reader ${ENV}`
- `uv run python -m ops.deploy_workload ${ENV}` (after edge removal)
- `terraform -chdir=infra/terraform/stacks/20-workload output`
- `terraform -chdir=infra/terraform/stacks/21-workload-mcp output`

## Parity risks
- Removing edge stack requires adding custom domain bindings directly to reader/search/MCP stacks.
- Auth service needs Key Vault access policy + managed identity wiring; missing RBAC will break auth.
- Key Vault IP rules may block ACA runtime if public access is restricted.
