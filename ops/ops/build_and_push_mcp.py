from __future__ import annotations

from pathlib import Path

from .build_and_push import build_cli


def main(argv: list[str] | None = None) -> int:
    return build_cli(
        argv=argv,
        description="Build and push the az-jina-mcp container image to Azure Container Registry.",
        target="az-jina-mcp",
        dockerfile=Path("az-jina-mcp/Dockerfile"),
        build_context=Path("az-jina-mcp"),
        include_paths=[
            Path("acr-build.yaml"),
            Path("az-jina-mcp/Dockerfile"),
            Path("az-jina-mcp/entrypoint.sh"),
            Path("az-jina-mcp/package.json"),
            Path("az-jina-mcp/package-lock.json"),
            Path("az-jina-mcp/tsconfig.json"),
            Path("az-jina-mcp/wrangler.jsonc"),
            Path("az-jina-mcp/worker-configuration.d.ts"),
            Path("az-jina-mcp/src"),
        ],
        tfvars_key="container_image",
        workload_stack="21-workload-mcp",
        image_repo_env="AZ_JINA_MCP_IMAGE_REPOSITORY_PREFIX",
        default_image_repo="az-jina-mcp",
        registry_login_env="AZ_JINA_MCP_REGISTRY_LOGIN_SERVER",
    )


if __name__ == "__main__":
    raise SystemExit(main())
