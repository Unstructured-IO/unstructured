#!/usr/bin/env bash
# Offline model of GitHub's documented concurrency queue; no workflows are run.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
workflow="$script_dir/../.github/workflows/post-release-dev-bump.yml"
# Read only the workflow-level block, so job keys cannot satisfy this contract.
config=$(sed -n '/^concurrency:/,/^[^ #]/p' "$workflow")
group=$(sed -n 's/^  group: //p' <<<"$config")
queue=$(sed -n 's/^  queue: //p' <<<"$config")
cancel=$(sed -n 's/^  cancel-in-progress: //p' <<<"$config")
[[ $group == post-release-dev-bump && $cancel == false ]] || {
  echo 'FAIL: all bump writers must share one non-canceling group' >&2
  exit 1
}
# This models only the two documented queue modes. Fail closed on unknown config.
[[ $queue == max || $queue == single || -z $queue ]] || exit 1
arrivals() {
  local running=$1 pending=() request
  shift
  for request in "$@"; do
    if [[ $queue == max ]]; then
      # A full queue rejects newcomers; it never replaces accepted pending work.
      if ((${#pending[@]} < 100)); then pending+=("$request"); fi
    else
      pending=("$request")
    fi
  done
  printf '%s\n' "$running" "${pending[@]}"
}
assert_preserved() {
  local actual expected
  expected=$(printf '%s\n' "$@")
  actual=$(arrivals "$@")
  [[ $actual == "$expected" ]] || {
    printf 'FAIL: accepted release work was replaced\n%s\n' "$actual" >&2
    exit 1
  }
  echo "ok - queued arrivals preserved: $*"
}
assert_preserved V0.27.35 v0.27.35 V0.27.35
assert_preserved 0.27.34 0.27.35 0.27.34
assert_preserved opencv-4.12.0.88 0.27.35 opencv-4.12.0.88
assert_preserved 0.27.35 v0.27.35 unstructured_0.27.35 unstructured_v0.27.35
assert_preserved 0.27.35 0.27.35 0.27.35

# Queued runs must checkout main after entering the workflow-level lock, then
# compute their plan. A plan carried in from another job would be stale.
[[ $(sed -n '/^jobs:/,$p' "$workflow" | sed -n '/^  [a-zA-Z_-]*:/p') == '  bump:' ]]
checkout_line=$(sed -n '/uses: actions\/checkout@/=' "$workflow")
plan_line=$(sed -n '/id: plan/=' "$workflow")
[[ $checkout_line -lt $plan_line ]]
grep -Fqx '          ref: main' "$workflow"
# Shared aliases produce one branch while main is final, and a completed bump
# turns every alias (including a late stale retry) into a no-op.
for tag in 0.27.35 v0.27.35 unstructured_0.27.35 unstructured_v0.27.35; do
  plan=$(bash "$script_dir/post-release-dev-bump.sh" "$tag" 0.27.35)
  [[ $plan == $'action=bump\nreleased=0.27.35\nnext=0.27.36-dev' ]]
  [[ $(bash "$script_dir/post-release-dev-bump.sh" "$tag" 0.27.36-dev) == action=noop ]]
  [[ $(bash "$script_dir/post-release-dev-bump.sh" "$tag" 0.28.0-dev) == action=noop ]]
done
echo 'ok - serialized aliases reuse one target and replan against current main'
