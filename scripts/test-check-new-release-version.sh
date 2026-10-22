#!/usr/bin/env bash
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
guard="$script_dir/check-new-release-version.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf '%s\n' v0.27.35 unstructured_0.27.34 0.17.11-dev1 opencv-4.12.0.88 0.8.1-docs-rebuild 0.9.0-docs-build >"$tmp/tags"
: >"$tmp/empty"
count=0
check() {
  local expected=$1 name=$2 status=0
  shift 2
  bash "$guard" "$@" >"$tmp/output" 2>&1 || status=$?
  if [[ $status != "$expected" ]]; then
    echo "FAIL: $name (expected $expected, got $status)"
    cat "$tmp/output"
    exit 1
  fi
  if [[ -n ${EXPECT_MESSAGE:-} ]] && ! grep -Fq -- "$EXPECT_MESSAGE" "$tmp/output"; then
    echo "FAIL: $name (missing message: $EXPECT_MESSAGE)"
    cat "$tmp/output"
    exit 1
  fi
  count=$((count + 1))
  echo "ok $count - $name"
}
EXPECT_MESSAGE="no tag lookup" check 0 'unchanged dev skips even an unreadable tag source' 0.27.35-dev 0.27.35-dev "$tmp/missing"
EXPECT_MESSAGE="no tag lookup" check 0 'unchanged dev ignores newer final' 0.27.34-dev 0.27.34-dev "$tmp/tags"
EXPECT_MESSAGE="no tag lookup" check 0 'bare dev equals dev0' 0.27.35-dev 0.27.35-dev0 "$tmp/missing"
EXPECT_MESSAGE="no tag lookup" check 0 'dot dev equals hyphen dev' 0.27.35.dev0 0.27.35-dev "$tmp/missing"
check 0 'release PR with no tag' 0.27.36 0.27.36-dev "$tmp/tags"
EXPECT_MESSAGE="next -dev bump must land first" check 1 'ordinary PR on final base' 0.27.35 0.27.35 "$tmp/missing"
EXPECT_MESSAGE="next -dev bump must land first" check 1 'queue entry behind release PR' 0.27.36 0.27.36 "$tmp/missing"
EXPECT_MESSAGE="already tagged" check 1 'existing v-prefixed final tag' 0.27.35 0.27.35-dev "$tmp/tags"
EXPECT_MESSAGE="already tagged" check 1 'existing unstructured-prefixed final tag' 0.27.34 0.27.34-dev "$tmp/tags"
EXPECT_MESSAGE="below latest release tag" check 1 'changed dev below latest final' 0.27.35-dev3 0.27.34-dev "$tmp/tags"
check 0 'next development bump' 0.27.36-dev 0.27.35 "$tmp/tags"
check 0 'numeric patch ordering' 0.27.100-dev 0.27.35 "$tmp/tags"
printf '%s\n' 1.0.0 >"$tmp/major"
EXPECT_MESSAGE="below latest release tag" check 1 'numeric major ordering' 0.99.99-dev 1.0.0 "$tmp/major"
printf '%s\n' 0.17.11-dev1 opencv-4.12.0.88 0.8.1-docs-rebuild 0.9.0-docs-build >"$tmp/ignored"
check 0 'non-version and dev tags ignored' 0.1.0-dev 0.0.1 "$tmp/ignored"
check 0 'dev tags do not reserve final release' 0.17.11 0.17.11-dev1 "$tmp/ignored"
check 0 'large numeric components avoid overflow' 999999999999999999999999.0.0-dev 0.27.35 "$tmp/tags"
check 1 'invalid merge version' broken 0.27.35 "$tmp/empty"
check 1 'invalid base version' 0.27.35-dev broken "$tmp/empty"

# Exercise the actual default invocation and Git merge semantics. The PR head
# retains the old version, while main releases and bumps after the PR branches.
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_NOSYSTEM=1
unset VERSION_BASE_REF
mkdir "$tmp/repo"
cd "$tmp/repo"
git init -q
git config user.name 'Version guard test'
git config user.email 'version-guard@example.invalid'
mkdir unstructured
printf '__version__ = "0.27.35-dev"\n' >unstructured/__version__.py
git add .
git commit -qm initial
git branch -M main
git checkout -qb ordinary-pr
printf 'ordinary change\n' >ordinary.txt
git add .
git commit -qm ordinary
pr_head=$(git rev-parse HEAD)
git checkout -q main
printf '__version__ = "0.27.35"\n' >unstructured/__version__.py
git commit -qam release
git tag 0.27.35
printf '__version__ = "0.27.36-dev"\n' >unstructured/__version__.py
git commit -qam bump
git update-ref refs/remotes/origin/main HEAD
git merge --no-ff -qm 'PR merge result' ordinary-pr
[[ $(git show "$pr_head:unstructured/__version__.py") == '__version__ = "0.27.35-dev"' ]]
[[ $(git show HEAD:unstructured/__version__.py) == '__version__ = "0.27.36-dev"' ]]
# No origin remote exists: any attempted tag fetch would fail this test.
EXPECT_MESSAGE="no tag lookup" check 0 'stale PR after release and bump uses merge result'
# Simulate an obsolete PR event base. The merge parent stays aligned with HEAD.
VERSION_BASE_REF=HEAD^1 EXPECT_MESSAGE="no tag lookup" check 0 'PR merge parent wins over obsolete event base'
# A real queue base can be a release commit ahead of origin/main.
git checkout -qb queue-release
printf '__version__ = "0.27.36"\n' >unstructured/__version__.py
git commit -qam queue-release
queue_base=$(git rev-parse HEAD)
printf 'queued change\n' >queued.txt
git add .
git commit -qm queue-entry
VERSION_BASE_REF=$queue_base EXPECT_MESSAGE="next -dev bump must land first" check 1 'merge-group uses release commit ahead as base'
# Read remote tag names without fetching tag objects or changing local tags.
git init -q --bare "$tmp/remote"
git remote add origin "$tmp/remote"
git push -q origin HEAD:refs/heads/main
remote_commit=$(git rev-parse HEAD)
git --git-dir="$tmp/remote" tag 0.27.36 "$remote_commit"
check 0 'changed version reads remote tag names' 0.27.37-dev 0.27.36
if git show-ref --verify --quiet refs/tags/0.27.36; then
  echo 'FAIL: tag discovery must not fetch tag objects'
  exit 1
fi
EXPECT_MESSAGE="already tagged" check 1 'remote final tag prevents release' 0.27.36 0.27.36-dev
git remote remove origin
check 128 'tag lookup failure fails closed' 0.27.37-dev 0.27.36
printf 'Passed %s version guard tests.\n' "$count"
