#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
generated="$(mktemp)"
committed="$(mktemp)"
trap 'rm -f "$generated" "$committed"' EXIT

cd "$repo_root"
uv export \
  --quiet \
  --frozen \
  --no-dev \
  --no-emit-project \
  --format requirements-txt \
  --no-header \
  --output-file "$generated"
tail -n +3 lambdas/requirements.txt >"$committed"

if ! diff -u "$committed" "$generated"; then
  echo "ERROR: lambdas/requirements.txt does not match uv.lock." >&2
  echo "Regenerate it with:" >&2
  echo "  uv export --frozen --no-dev --no-emit-project --format requirements-txt --output-file lambdas/requirements.txt" >&2
  exit 1
fi
