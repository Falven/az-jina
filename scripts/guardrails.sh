#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "guardrails: $*" >&2
  exit 1
}

if [ -d "reader-runtime" ]; then
  fail "reader-runtime/ exists"
fi

for name in edge gateway ingress-proxy; do
  if [ -d "${name}" ]; then
    fail "${name}/ exists"
  fi
done

allowed=(
  "az-reader/Dockerfile"
  "mcp-runtime/Dockerfile"
  "services/auth/Dockerfile"
)

list_dockerfiles() {
  if command -v rg >/dev/null 2>&1; then
    rg --files -g "Dockerfile" -g "!node_modules" -g "!**/.venv" || true
  else
    find . -type f -name Dockerfile -not -path "*/node_modules/*" -not -path "*/.venv/*"
  fi
}

while IFS= read -r path; do
  if [ -z "${path}" ]; then
    continue
  fi
  clean=${path#./}
  allowed_match=false
  for ok in "${allowed[@]}"; do
    if [ "${clean}" = "${ok}" ]; then
      allowed_match=true
      break
    fi
  done
  if [ "${allowed_match}" = false ]; then
    fail "Unexpected Dockerfile: ${clean}"
  fi
done < <(list_dockerfiles)

echo "guardrails: ok"
