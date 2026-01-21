from __future__ import annotations

import argparse
import logging
import re
import secrets
import string
import subprocess
from typing import Any

from ._deploy_common import (
    azure_context,
    configure_logging,
    ensure_tfvars,
    load_tfvars,
    resolve_paths,
)
from ._utils import ensure, run_logged

KEY_ID_RE = re.compile(r"^[a-zA-Z0-9-]{6,64}$")
PREFIX_RE = re.compile(r"^[a-zA-Z0-9-]{3,32}$")


def _run_az(command: list[str]) -> str:
    ensure(["az"])
    result = run_logged(command, capture_output=True, echo="on_error")
    return result.stdout


def _load_tfvars_data(env: str) -> dict[str, Any]:
    paths = resolve_paths(workload_stack="20-workload")
    ctx = azure_context()
    tfvars = ensure_tfvars(paths.workload, env, ctx.subscription_id, ctx.tenant_id)
    try:
        return load_tfvars(tfvars)
    except Exception as exc:
        raise RuntimeError(f"Failed to read tfvars at {tfvars}") from exc


def _validate_prefix(prefix: str) -> str:
    candidate = prefix.strip()
    if candidate == "" or not PREFIX_RE.match(candidate):
        raise ValueError(
            "API key prefix must be 3-32 chars (letters, digits, hyphen)."
        )
    return candidate


def _resolve_prefix(tfvars_data: dict[str, Any], override: str | None) -> str:
    if override:
        return _validate_prefix(override)
    app_settings = tfvars_data.get("app_settings", {})
    if isinstance(app_settings, dict):
        raw = str(app_settings.get("API_KEY_PREFIX", "") or "").strip()
        if raw:
            return _validate_prefix(raw)
    return _validate_prefix("azjina")


def _resolve_vault(tfvars_data: dict[str, Any], vault_override: str | None) -> str:
    vault = vault_override or str(tfvars_data.get("key_vault_name", "") or "").strip()
    if vault == "":
        raise RuntimeError(
            "Key Vault name is required. Set key_vault_name in tfvars or pass --vault-name."
        )
    return vault


def _generate_key_id(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _generate_secret(length: int = 48) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _validate_key_id(key_id: str) -> str:
    candidate = key_id.strip()
    if candidate == "" or not KEY_ID_RE.match(candidate):
        raise ValueError(
            "Key ID must be 6-64 chars (letters, digits, hyphen)."
        )
    return candidate


def _parse_full_token(token: str) -> tuple[str, str, str] | None:
    parts = token.split("_")
    if len(parts) < 3:
        return None
    prefix = parts[0].strip()
    key_id = parts[1].strip()
    secret = "_".join(parts[2:]).strip()
    if prefix == "" or key_id == "" or secret == "":
        return None
    return prefix, key_id, secret


def _build_token(prefix: str, key_id: str, secret: str) -> str:
    return f"{prefix}_{key_id}_{secret}"


def _secret_name(prefix: str, key_id: str) -> str:
    return f"{prefix}-api-key-{key_id}"


def _list_secret_names(vault: str, prefix: str) -> list[str]:
    query = f"[?starts_with(name, '{prefix}-api-key-')].name"
    output = _run_az(
        [
            "az",
            "keyvault",
            "secret",
            "list",
            "--vault-name",
            vault,
            "--query",
            query,
            "--output",
            "tsv",
        ]
    ).strip()
    if output == "":
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _get_secret_value(vault: str, name: str) -> str | None:
    try:
        output = _run_az(
            [
                "az",
                "keyvault",
                "secret",
                "show",
                "--vault-name",
                vault,
                "--name",
                name,
                "--query",
                "value",
                "--output",
                "tsv",
            ]
        ).strip()
    except subprocess.CalledProcessError:
        return None
    return output or None


def _set_secret_value(vault: str, name: str, value: str) -> None:
    _run_az(
        [
            "az",
            "keyvault",
            "secret",
            "set",
            "--vault-name",
            vault,
            "--name",
            name,
            "--value",
            value,
        ]
    )


def _delete_secret(vault: str, name: str) -> None:
    _run_az(
        [
            "az",
            "keyvault",
            "secret",
            "delete",
            "--vault-name",
            vault,
            "--name",
            name,
        ]
    )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--env",
        default="dev",
        help="Environment code (e.g. dev, prod). Used to locate tfvars defaults.",
    )
    parser.add_argument(
        "--vault-name",
        help="Key Vault name. Defaults to key_vault_name in tfvars for --env.",
    )
    parser.add_argument(
        "--prefix",
        help="API key prefix. Defaults to app_settings.API_KEY_PREFIX or azjina.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage API keys stored in Azure Key Vault."
    )
    _add_common_args(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new API key.")
    _add_common_args(create_parser)
    create_parser.add_argument(
        "--name",
        help="Key ID (6-64 chars). Generated if omitted.",
    )
    create_parser.add_argument(
        "--token",
        help="Optional full token (prefix_keyId_secret) or secret value.",
    )

    list_parser = subparsers.add_parser("list", help="List API keys.")
    _add_common_args(list_parser)
    list_parser.add_argument(
        "--hide-secret",
        action="store_true",
        help="Deprecated (list never emits secrets).",
    )

    revoke_parser = subparsers.add_parser("revoke", help="Revoke API keys.")
    _add_common_args(revoke_parser)
    revoke_parser.add_argument(
        "--name",
        action="append",
        required=True,
        help="Key ID to revoke (repeatable).",
    )

    args = parser.parse_args(argv)
    configure_logging()

    tfvars_data = _load_tfvars_data(args.env)
    vault = _resolve_vault(tfvars_data, args.vault_name)
    prefix = _resolve_prefix(tfvars_data, args.prefix)

    if args.command == "create":
        token_override: str | None = args.token
        parsed = _parse_full_token(token_override) if token_override else None
        if parsed:
            parsed_prefix, parsed_key_id, parsed_secret = parsed
            prefix_ok = _validate_prefix(parsed_prefix) == prefix
            name_ok = args.name is None or _validate_key_id(args.name) == parsed_key_id
            if prefix_ok and name_ok:
                key_id = _validate_key_id(parsed_key_id)
                secret = parsed_secret
            else:
                key_id = _validate_key_id(args.name) if args.name else _generate_key_id()
                secret = token_override or _generate_secret()
        else:
            key_id = _validate_key_id(args.name) if args.name else _generate_key_id()
            secret = token_override or _generate_secret()

        secret_name = _secret_name(prefix, key_id)
        _set_secret_value(vault, secret_name, secret)
        token = _build_token(prefix, key_id, secret)
        logging.info("vault=%s", vault)
        logging.info("prefix=%s", prefix)
        logging.info("key_id=%s", key_id)
        logging.info("token=%s", token)
        return 0

    if args.command == "list":
        secret_names = _list_secret_names(vault, prefix)
        logging.info("vault=%s", vault)
        logging.info("prefix=%s", prefix)
        for name in sorted(secret_names):
            key_id = name.replace(f"{prefix}-api-key-", "", 1)
            logging.info("%s", key_id)
        return 0

    if args.command == "revoke":
        removed: list[str] = []
        for key_id in args.name:
            validated = _validate_key_id(key_id)
            secret_name = _secret_name(prefix, validated)
            _delete_secret(vault, secret_name)
            removed.append(validated)
        logging.info("vault=%s", vault)
        logging.info("prefix=%s", prefix)
        logging.info("removed_ids=%s", ",".join(sorted(removed)))
        return 0

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
