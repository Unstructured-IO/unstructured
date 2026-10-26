#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
check() {
  local expected=$1 message=$2 status=0 output
  shift 2
  output=$(bash "$script_dir/post-release-dev-bump.sh" "$@" 2>&1) || status=$?
  if [[ $status != "$expected" || $output != *"$message"* ]]; then
    printf 'FAIL: %s (status %s)\n%s\n' "$*" "$status" "$output"
    exit 1
  fi
  echo "ok - $*"
}
# Successful plans must emit the complete bump decision, not just a version.
bump() { printf 'action=bump\nreleased=%s\nnext=%s' "$1" "$2"; }
check 0 "$(bump 0.27.35 0.27.36-dev)" 0.27.35 0.27.35
check 0 "$(bump 0.27.35 0.27.36-dev)" v0.27.35 0.27.35
check 0 "$(bump 0.27.35 0.27.36-dev)" unstructured_0.27.35 0.27.35
check 0 "$(bump 0.27.35 0.27.36-dev)" unstructured_v0.27.35 0.27.35
check 0 "$(bump 1.2.99 1.2.100-dev)" 1.2.99 1.2.99
check 0 "$(bump 1.2.999999999999999999999 1.2.1000000000000000000000-dev)" 1.2.999999999999999999999 1.2.999999999999999999999
for tag in opencv-4.12.0.88 0.8.1-docs-rebuild 1.2.3-dev 1.2.3.dev1 1.2.3rc1 bad '1.2.3;exit' 01.2.3 V0.27.35 UNSTRUCTURED_0.27.35 unstructured_V0.27.35; do
  check 0 'action=skip' "$tag" 0.27.35
done
check 0 'action=noop' 0.27.35 0.27.36-dev
check 0 'action=noop' 0.27.35 0.27.36-dev2
check 0 'action=noop' 0.27.35 0.28.0-dev
for current in 0.27.36.dev 0.27.36.dev0 0.27.36.dev2 0.28.0.dev1; do
  check 0 'action=noop' 0.27.35 "$current"
done
for current in 0.27.35.dev9 0.27.36.dev2junk 0.27.36-rc1; do
  check 1 'Unexpected main version' 0.27.35 "$current"
done
check 1 'Unexpected main version' 0.27.35 0.27.36
check 1 'Unexpected main version' 0.27.35 0.27.34
check 1 'Unexpected main version' 0.27.35 0.27.35-dev9
check 1 'Unexpected main version' 0.27.35 broken

# Exercise main's version-file format, including its coverage comment.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_NOSYSTEM=1
mkdir "$tmp/repo"
cd "$tmp/repo"
git init -q
git config user.name 'Bump test'
git config user.email 'bump@example.invalid'
mkdir unstructured
printf '__version__ = "0.27.35"  # pragma: no cover\n' >unstructured/__version__.py
git add .
git commit -qm release
check 0 "$(bump 0.27.35 0.27.36-dev)" 0.27.35
NEXT_VERSION=0.27.36-dev
sed "s/^\(__version__ = \"\)[^\"]*\(\"\)/\1$NEXT_VERSION\2/" unstructured/__version__.py >"$tmp/updated"
[[ $(cat "$tmp/updated") == '__version__ = "0.27.36-dev"  # pragma: no cover' ]]
echo 'ok - update preserves version-file comment'

# Mock the read-only GitHub query; no network or credentials are needed.
gh() {
  [[ $* == 'release view 0.27.35 --json isDraft,isPrerelease,publishedAt --jq '* ]] || return 2
  printf '%s\n' "$MOCK_PUBLISHED"
  return "$MOCK_STATUS"
}
export -f gh
export MOCK_PUBLISHED=true MOCK_STATUS=0
check 0 '' --verify-release 0.27.35
MOCK_PUBLISHED=false check 1 'published final GitHub Release' --verify-release 0.27.35
MOCK_STATUS=1 check 1 'published final GitHub Release' --verify-release 0.27.35

# Check the queue contract and its arrival scenarios separately from planning.
bash "$script_dir/test-post-release-dev-bump-queue.sh"
