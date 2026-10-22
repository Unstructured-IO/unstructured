#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
count=0
check() {
  local expected=$1 name=$2 current=$3 base=$4 tags=$5 status=0 output
  output=$(bash scripts/check-new-release-version.sh "$current" "$base" <<<"$tags" 2>&1) || status=$?
  if [[ $status != "$expected" ]]; then
    printf 'FAIL: %s (expected %s, got %s)\n%s\n' "$name" "$expected" "$status" "$output" >&2
    exit 1
  fi
  count=$((count + 1))
}
check 0 'dev PR on dev main' 0.27.35-dev 0.27.35-dev $'0.27.34\n0.17.11-dev1'
check 0 'release PR' 0.27.35 0.27.35-dev 0.27.34
check 1 'ordinary PR on final main' 0.27.35 0.27.35 0.27.34
check 1 'queue entry behind release PR' 0.27.35 0.27.35 ''
check 1 'tagged final' 0.27.35 0.27.35-dev v0.27.35
check 1 'prefixed tagged final' 0.27.35 0.27.35-dev unstructured_0.27.35
check 1 'backward dev bump' 0.27.34-dev1 0.27.35-dev 0.27.34
check 0 'bare dev equals dev0 tag' 0.27.35-dev 0.27.35-dev0 0.27.35-dev0
check 0 'dev0 equals dotted dev tag' 0.27.35-dev0 0.27.35.dev0 0.27.35.dev0
check 0 'ignore non-package tags' 0.27.35-dev 0.27.35-dev $'opencv-4.12.0.88\n0.8.1-docs-rebuild\n0.9.0-docs-build'
check 0 'dev tags are not final releases' 0.27.35-dev1 0.27.35-dev 0.27.36-dev9
check 0 'numeric major ordering' 10.0.0-dev 9.0.0-dev 9.99.99
check 1 'numeric patch ordering' 0.27.9-dev 0.27.35-dev 0.27.10
check 0 'final after dev tag' 0.27.35 0.27.35-dev 0.27.35-dev3
check 1 'invalid current fails closed' 0.27.35-bogus 0.27.35-dev ''
check 1 'invalid base fails closed' 0.27.35-dev bogus ''
printf 'Passed %s version guard cases.\n' "$count"
