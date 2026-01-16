# az-jina

Top-level repo that keeps az-jina-mcp and az-reader as submodules, with shared infra and ops.

Layout
- az-jina-mcp/ (submodule)
- az-reader/ (submodule)
- infra/ (merged Terraform)
- ops/ (shared deployment helpers)

Infra stacks
- infra/terraform/stacks/00-bootstrap: shared tfstate RG + storage account (local state under .state/)
- infra/terraform/stacks/20-workload: az-reader workload (creates shared RG + ACA env)
- infra/terraform/stacks/21-workload-mcp: az-jina-mcp workload (reuses shared RG + ACA env)

Ops commands
- Bootstrap tfstate (shared):
  - cd ops
  - uv sync
  - uv run python -m ops.deploy_bootstrap dev
- Deploy Reader workload:
  - uv run python -m ops.deploy_workload_reader dev
- Deploy MCP workload:
  - uv run python -m ops.deploy_workload dev

Notes
- Shared RGs: workload = <workload-rg-name>, state = <state-rg-name>.
- Workload RG is shared via rg_name_override and aca_env_name_override in 20-workload tfvars.
- MCP reuses the shared ACA environment via existing_aca_environment_id in 21-workload-mcp tfvars.
- Workload state keys are split (e.g., <env>/reader/terraform.tfstate and <env>/mcp/terraform.tfstate).
