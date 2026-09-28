#!/usr/bin/env bash
# Scans the environment's dependencies with pip-audit, arguments passed through.
# Asks PyPI's vulnerability service, then OSV when PyPI can't be reached, so a
# PyPI outage (503s) doesn't read as vulnerabilities found.
set -uo pipefail

out=$(mktemp)
trap 'rm -f "$out"' EXIT

for service in pypi osv; do
    uv run pip-audit -s "$service" "$@" >"$out" 2>&1
    status=$?
    if ! grep -qE 'ServiceError|ConnectionError|HTTPError|Timeout' "$out"; then
        cat "$out"
        [ "$status" -eq 0 ] && exit 0
        echo "ERROR: pip-audit: security vulnerabilities found"
        exit 1
    fi
    echo "pip-audit: couldn't reach the $service vulnerability service:"
    grep -m1 -E 'Error' "$out"
done
echo "ERROR: pip-audit: no vulnerability service answered, so nothing was checked"
exit 1
