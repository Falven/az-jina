from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ._deploy_common import (
    AzureContext,
    BootstrapState,
    azure_context,
    configure_logging,
    ensure_tfvars,
    export_core_tf_env,
    load_bootstrap_state,
    resolve_paths,
    workload_state_key,
    terraform_apply,
    terraform_init_remote,
    terraform_output,
    terraform_plan,
    update_tfvars,
)
from ._utils import ensure
from .build_and_push import build_and_push


def deploy_workload(
    env: str,
    extra: list[str],
    *,
    local_docker: bool,
    registry_login_server: str | None,
) -> None:
    configure_logging()
    ensure(["az", "terraform"])
    ctx: AzureContext = azure_context()
    export_core_tf_env(env, ctx)
    paths_mcp = resolve_paths(workload_stack="21-workload-mcp")
    tfvars_mcp = ensure_tfvars(
        paths_mcp.workload, env, ctx.subscription_id, ctx.tenant_id
    )

    build_and_push(
        env=env,
        target="az-jina-mcp",
        dockerfile=Path("mcp-runtime/Dockerfile"),
        build_context=Path("."),
        include_paths=[
            Path("acr-build.yaml"),
            Path("package.json"),
            Path("pnpm-workspace.yaml"),
            Path("pnpm-lock.yaml"),
            Path("mcp-runtime/Dockerfile"),
            Path("mcp-runtime/package.json"),
            Path("mcp-runtime/tsconfig.json"),
            Path("mcp-runtime/src"),
            Path("az-jina-mcp/src"),
        ],
        local_docker=local_docker,
        tfvars_key="container_image",
        workload_stack="21-workload-mcp",
        image_repo_env="AZ_JINA_MCP_IMAGE_REPOSITORY_PREFIX",
        default_image_repo="az-jina-mcp",
        registry_login_env="AZ_JINA_MCP_REGISTRY_LOGIN_SERVER",
        registry_login_server=registry_login_server,
        tfvars_path=tfvars_mcp,
    )

    bootstrap_state = load_bootstrap_state(env, paths_mcp, ctx)
    state_key_mcp = workload_state_key(env, "mcp")
    update_tfvars(
        tfvars_mcp,
        {
            "state_resource_group_name": bootstrap_state.resource_group,
            "state_storage_account_name": bootstrap_state.storage_account,
            "state_container_name": bootstrap_state.container,
            "state_blob_key": state_key_mcp,
            "reader_state_blob_key": workload_state_key(env, "reader"),
        },
    )

    logging.info("==> 21-workload-mcp (%s)", env)
    terraform_init_remote(
        paths_mcp.workload,
        tenant_id=ctx.tenant_id,
        state_rg=bootstrap_state.resource_group,
        state_sa=bootstrap_state.storage_account,
        state_container=bootstrap_state.container,
        state_key=state_key_mcp,
    )
    terraform_plan(paths_mcp.workload, tfvars_mcp, extra)
    terraform_apply(paths_mcp.workload, tfvars_mcp, True, extra)
    _log_app_endpoints(paths_mcp.workload, "MCP")

    paths_auth = resolve_paths(workload_stack="23-workload-auth")
    tfvars_auth = ensure_tfvars(
        paths_auth.workload, env, ctx.subscription_id, ctx.tenant_id
    )

    build_and_push(
        env=env,
        target="az-jina-auth",
        dockerfile=Path("services/auth/Dockerfile"),
        build_context=Path("services/auth"),
        include_paths=[
            Path("acr-build.yaml"),
            Path("services/auth/Dockerfile"),
            Path("services/auth/pyproject.toml"),
            Path("services/auth/uv.lock"),
            Path("services/auth/auth_service"),
        ],
        local_docker=local_docker,
        tfvars_key="container_image",
        workload_stack="23-workload-auth",
        image_repo_env="AZ_JINA_AUTH_IMAGE_REPOSITORY_PREFIX",
        default_image_repo="az-jina-auth",
        registry_login_env="AZ_JINA_AUTH_REGISTRY_LOGIN_SERVER",
        registry_login_server=registry_login_server,
        tfvars_path=tfvars_auth,
    )

    state_key_auth = workload_state_key(env, "auth")
    update_tfvars(
        tfvars_auth,
        {
            "state_resource_group_name": bootstrap_state.resource_group,
            "state_storage_account_name": bootstrap_state.storage_account,
            "state_container_name": bootstrap_state.container,
            "state_blob_key": state_key_auth,
            "reader_state_blob_key": workload_state_key(env, "reader"),
        },
    )

    logging.info("==> 23-workload-auth (%s)", env)
    terraform_init_remote(
        paths_auth.workload,
        tenant_id=ctx.tenant_id,
        state_rg=bootstrap_state.resource_group,
        state_sa=bootstrap_state.storage_account,
        state_container=bootstrap_state.container,
        state_key=state_key_auth,
    )
    terraform_plan(paths_auth.workload, tfvars_auth, extra)
    terraform_apply(paths_auth.workload, tfvars_auth, True, extra)
    _log_app_endpoints(paths_auth.workload, "Auth")

    _update_reader_auth_base(
        env=env,
        extra=extra,
        ctx=ctx,
        bootstrap_state=bootstrap_state,
        auth_workload_path=paths_auth.workload,
    )


def _log_app_endpoints(workload_path: Path, label: str) -> None:
    outputs = terraform_output(workload_path)

    def _val(key: str) -> str | None:
        node = outputs.get(key, {})
        if isinstance(node, dict):
            value = node.get("value")
            return str(value) if value is not None else None
        return None

    app_fqdn = _val("container_app_fqdn")

    def _normalize(url: str | None) -> str | None:
        if url is None:
            return None
        return url if url.startswith("http") else f"https://{url}"

    logging.info("==> Deployment outputs")
    if app_fqdn:
        logging.info("%s app: %s", label, f"{_normalize(app_fqdn)}/")


def _update_reader_auth_base(
    *,
    env: str,
    extra: list[str],
    ctx: AzureContext,
    bootstrap_state: BootstrapState,
    auth_workload_path: Path,
) -> None:
    outputs = terraform_output(auth_workload_path)

    def _val(key: str) -> str | None:
        node = outputs.get(key, {})
        if isinstance(node, dict):
            value = node.get("value")
            return str(value) if value is not None else None
        return None

    auth_fqdn = _val("container_app_fqdn")
    if auth_fqdn is None or auth_fqdn == "":
        logging.warning("Auth FQDN missing; skipping reader auth base update.")
        return

    auth_base = auth_fqdn if auth_fqdn.startswith("http") else f"https://{auth_fqdn}"
    paths_reader = resolve_paths(workload_stack="20-workload")
    tfvars_reader = ensure_tfvars(
        paths_reader.workload, env, ctx.subscription_id, ctx.tenant_id
    )
    state_key_reader = workload_state_key(env, "reader")
    update_tfvars(
        tfvars_reader,
        {
            "state_resource_group_name": bootstrap_state.resource_group,
            "state_storage_account_name": bootstrap_state.storage_account,
            "state_container_name": bootstrap_state.container,
            "state_blob_key": state_key_reader,
            "auth_dashboard_base_url": auth_base,
        },
    )

    logging.info("==> 20-workload (auth base update)")
    terraform_init_remote(
        paths_reader.workload,
        tenant_id=ctx.tenant_id,
        state_rg=bootstrap_state.resource_group,
        state_sa=bootstrap_state.storage_account,
        state_container=bootstrap_state.container,
        state_key=state_key_reader,
    )
    terraform_plan(paths_reader.workload, tfvars_reader, extra)
    terraform_apply(paths_reader.workload, tfvars_reader, True, extra)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build, push, and deploy the 21-workload-mcp and 23-workload-auth stacks."
    )
    parser.add_argument(
        "env",
        help="Environment code (e.g. dev, prod). Used to select <env>.tfvars files.",
    )
    parser.add_argument(
        "--local-docker",
        action="store_true",
        help="Build with local Docker instead of ACR build.",
    )
    parser.add_argument(
        "--registry-login-server",
        help="Registry login server (e.g. myacr.azurecr.io). Overrides tfvars/env.",
    )
    args, extra = parser.parse_known_args(argv)

    registry_override = args.registry_login_server
    local_docker = args.local_docker
    cleaned_extra: list[str] = []
    skip_next = False
    for idx, token in enumerate(extra):
        if skip_next:
            skip_next = False
            continue
        if token == "--local-docker":
            local_docker = True
            continue
        if token == "--registry-login-server":
            if idx + 1 < len(extra):
                registry_override = extra[idx + 1]
                skip_next = True
            continue
        cleaned_extra.append(token)

    deploy_workload(
        args.env,
        cleaned_extra,
        local_docker=local_docker,
        registry_login_server=registry_override,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
