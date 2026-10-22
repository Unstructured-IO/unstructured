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
check 0 'next=0.27.36-dev' 0.27.35 0.27.35
check 0 'next=0.27.36-dev' v0.27.35 0.27.35
check 0 'next=1.2.100-dev' 1.2.99 1.2.99
check 0 'next=1.2.1000000000000000000000-dev' 1.2.999999999999999999999 1.2.999999999999999999999
for tag in opencv-4.12.0.88 0.8.1-docs-rebuild 1.2.3-dev 1.2.3.dev1 1.2.3rc1 bad '1.2.3;exit' 01.2.3; do
  check 0 'action=skip' "$tag" 0.27.35
done
check 0 'action=noop' 0.27.35 0.27.36-dev
check 0 'action=noop' 0.27.35 0.27.36-dev2
check 0 'action=noop' 0.27.35 0.28.0-dev
check 1 'Unexpected main version' 0.27.35 0.27.36
check 1 'Unexpected main version' 0.27.35 0.27.34
check 1 'Unexpected main version' 0.27.35 0.27.35-dev9
check 1 'Unexpected main version' 0.27.35 broken

# Exercise main's version-file format, including its coverage comment.
tmp=$(mktemp -d)
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
check 0 'next=0.27.36-dev' 0.27.35
NEXT_VERSION=0.27.36-dev
sed "s/^\(__version__ = \"\)[^\"]*\(\"\)/\1$NEXT_VERSION\2/" unstructured/__version__.py >"$tmp/updated"
[[ $(cat "$tmp/updated") == '__version__ = "0.27.36-dev"  # pragma: no cover' ]]
echo 'ok - update preserves version-file comment'
