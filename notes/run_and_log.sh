#!/usr/bin/env bash
set -euo pipefail

cmd="$*"
if [ -z "${cmd}" ]; then
  echo "Usage: run_and_log.sh <command>" >&2
  exit 2
fi

mkdir -p notes
log="notes/commands.log"
: >> "${log}"

set +e
output="$(bash -lc "${cmd}" 2>&1)"
status=$?
set -e

printf "COMMAND: %s\nEXIT: %s\nOUTPUT:\n%s\n---\n" "${cmd}" "${status}" "${output}" >> "${log}"
printf "%s" "${output}"
exit "${status}"
