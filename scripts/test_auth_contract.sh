#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${AUTH_BASE_URL:-http://localhost:8080}
DASHBOARD_KEY=${AUTH_DASHBOARD_API_KEY:?AUTH_DASHBOARD_API_KEY is required}
TOKEN=${AUTH_TEST_TOKEN:?AUTH_TEST_TOKEN is required}

HEADER_AUTH=("Authorization: Bearer ${DASHBOARD_KEY}")
HEADER_JSON=("Content-Type: application/json" "Accept: application/json")

require_status() {
  local expected=$1
  local path=$2
  local body=$3
  local out
  out=$(mktemp)
  local status
  status=$(curl -sS -o "${out}" -w "%{http_code}" \
    -H "${HEADER_AUTH[0]}" \
    -H "${HEADER_JSON[0]}" \
    -H "${HEADER_JSON[1]}" \
    -X POST "${BASE_URL}${path}" \
    -d "${body}")
  local log_body
  log_body=${body}
  log_body=${log_body//${TOKEN}/REDACTED}
  if [[ -n "${AUTH_TEST_INVALID_TOKEN:-}" ]]; then
    log_body=${log_body//${AUTH_TEST_INVALID_TOKEN}/REDACTED}
  fi
  if [[ -n "${AUTH_TEST_QUOTA_TOKEN:-}" ]]; then
    log_body=${log_body//${AUTH_TEST_QUOTA_TOKEN}/REDACTED}
  fi
  echo "${status} ${path} ${log_body}"
  cat "${out}"
  echo ""
  rm -f "${out}"
  if [[ "${status}" != "${expected}" ]]; then
    echo "Expected ${expected} for ${path}, got ${status}" >&2
    exit 1
  fi
}

echo "Testing auth contract against ${BASE_URL}"

require_status 200 "/authorization" "{\"token\":\"${TOKEN}\"}"
require_status 200 "/validate" "{\"token\":\"${TOKEN}\"}"
require_status 200 "/usage" "{\"token\":\"${TOKEN}\",\"model_name\":\"reader-crawl\",\"api_endpoint\":\"/\",\"consumer\":{\"id\":\"user\",\"user_id\":\"user\"},\"usage\":{\"total_tokens\":1},\"labels\":{\"model_name\":\"reader-crawl\"}}"

require_status 401 "/authorization" "{}"

if [[ -n "${AUTH_TEST_INVALID_TOKEN:-}" ]]; then
  require_status 401 "/authorization" "{\"token\":\"${AUTH_TEST_INVALID_TOKEN}\"}"
fi

if [[ -n "${AUTH_TEST_QUOTA_TOKEN:-}" ]]; then
  require_status 402 "/authorization" "{\"token\":\"${AUTH_TEST_QUOTA_TOKEN}\"}"
fi

echo "Auth contract checks passed."
