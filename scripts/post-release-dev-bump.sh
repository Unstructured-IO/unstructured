#!/usr/bin/env bash
# Print an action and versions; this script never changes the checkout.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# CI checks each script separately; the shared functions are checked on their own.
# shellcheck disable=SC1091
source "$script_dir/check-new-release-version.sh"

plan_bump() {
  local tag=${1#v} current=$2 patch next digit carry=1 result='' i
  if [[ ! $tag =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
    echo "Skip non-package release: $1" >&2
    echo 'action=skip'
    return 0
  fi
  patch=${BASH_REMATCH[3]}
  # Decimal increment avoids shell integer overflow on arbitrary tag inputs.
  for ((i = ${#patch} - 1; i >= 0; i--)); do
    digit=$((10#${patch:i:1} + carry))
    carry=$((digit / 10))
    result="$((digit % 10))$result"
  done
  if ((carry)); then result="1$result"; fi
  next="${tag%.*}.$result-dev"
  if [[ $current == "$tag" ]]; then
    printf 'action=bump\nreleased=%s\nnext=%s\n' "$tag" "$next"
  elif [[ $current =~ ^[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]*$ ]] && ! version_less "$current" "$next"; then
    echo "No-op: main already holds $current (at least $next)." >&2
    echo 'action=noop'
  else
    echo "::error::Unexpected main version $current after release $tag; expected $tag or development version >= $next. No changes made." >&2
    return 1
  fi
}

verify_release() {
  local published
  if ! published=$(gh release view "$1" --json isDraft,isPrerelease,publishedAt --jq '.isDraft == false and .isPrerelease == false and .publishedAt != null') || [[ $published != true ]]; then
    echo "::error::Tag $1 must identify a published final GitHub Release. No changes made." >&2
    return 1
  fi
}

if [[ ${1:-} == --verify-release ]]; then
  verify_release "$2"
elif [[ $# == 1 ]]; then
  plan_bump "$1" "$(read_version HEAD)"
else
  plan_bump "$@"
fi
