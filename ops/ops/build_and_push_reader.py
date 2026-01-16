from __future__ import annotations

from pathlib import Path

from .build_and_push import build_cli


def main(argv: list[str] | None = None) -> int:
    return build_cli(
        argv=argv,
        description="Build and push the az-reader container image to Azure Container Registry.",
        target="az-reader",
        dockerfile=Path("az-reader/Dockerfile"),
        build_context=Path("az-reader"),
        include_paths=[
            Path("acr-build.yaml"),
            Path("az-reader/Dockerfile"),
            Path("az-reader/package.json"),
            Path("az-reader/package-lock.json"),
            Path("az-reader/build"),
            Path("az-reader/public"),
            Path("az-reader/licensed"),
        ],
        tfvars_key="container_image",
        workload_stack="20-workload",
        image_repo_env="AZ_READER_IMAGE_REPOSITORY_PREFIX",
        default_image_repo="az-reader",
        registry_login_env="AZ_READER_REGISTRY_LOGIN_SERVER",
    )


if __name__ == "__main__":
    raise SystemExit(main())
