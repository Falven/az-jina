#!/usr/bin/env bash
set -euo pipefail

check_branch() {
  local name=$1
  local path=$2
  local expected=$3
  if [ ! -d "${path}" ]; then
    echo "${name}: missing at ${path}" >&2
    exit 1
  fi
  local branch
  branch=$(git -C "${path}" rev-parse --abbrev-ref HEAD)
  if [ "${branch}" != "${expected}" ]; then
    echo "${name}: expected branch ${expected}, got ${branch}" >&2
    exit 1
  fi
  if [ -n "$(git -C "${path}" status --porcelain)" ]; then
    echo "${name}: working tree dirty" >&2
    git -C "${path}" status -sb
    exit 1
  fi
  echo "${name}: branch ${branch} clean"
  git -C "${path}" status -sb
  git -C "${path}" diff --stat
}

check_branch "az-reader" "az-reader" "feature/az"
check_branch "az-jina-mcp" "az-jina-mcp" "feature/az"

