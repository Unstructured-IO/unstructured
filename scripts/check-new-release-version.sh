#!/usr/bin/env bash
# Usage: check-new-release-version.sh VERSION BASE_VERSION < tags.txt
# Or: check-new-release-version.sh --git BASE_REF (tags must already be fetched).
set -euo pipefail

# Normalize the supported package versions into a numeric tuple. Final sorts last.
parse_version() {
  local value=$1 part
  local pattern='^([0-9]+)\.([0-9]+)\.([0-9]+)((-dev|\.dev)([0-9]*))?$'
  [[ $value =~ $pattern ]] || return 1
  local parts=("${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}")
  if [[ -n ${BASH_REMATCH[4]} ]]; then
    parts+=(0 "${BASH_REMATCH[6]:-0}")
  else
    parts+=(1 0)
  fi
  for part in "${parts[@]}"; do
    while [[ ${#part} -gt 1 && $part == 0* ]]; do part=${part#0}; done
    printf '%s ' "$part"
  done
  printf '\n'
}

# Compare decimal strings without integer overflow or octal interpretation.
compare_versions() {
  local left right i
  read -r -a left <<<"$1"
  read -r -a right <<<"$2"
  for i in 0 1 2 3 4; do
    if [[ ${#left[i]} -gt ${#right[i]} ]]; then
      echo 1
      return
    fi
    if [[ ${#left[i]} -lt ${#right[i]} ]]; then
      echo -1
      return
    fi
    if [[ ${left[i]} > ${right[i]} ]]; then
      echo 1
      return
    fi
    if [[ ${left[i]} < ${right[i]} ]]; then
      echo -1
      return
    fi
  done
  echo 0
}

read_version() {
  local content=$1
  # The package version assignment uses double quotes.
  local pattern='__version__[[:space:]]*=[[:space:]]*"([^"]+)"'
  [[ $content =~ $pattern ]] || {
    echo 'Cannot read package version' >&2
    return 1
  }
  printf '%s\n' "${BASH_REMATCH[1]}"
}

if [[ ${1:-} == --git && $# == 2 ]]; then
  current=$(read_version "$(cat unstructured/__version__.py)")
  base=$(read_version "$(git show "$2:unstructured/__version__.py")")
  tags=$(git tag --list)
elif [[ $# == 2 ]]; then
  current=$1
  base=$2
  tags=$(cat)
else
  echo 'Usage: check-new-release-version.sh VERSION BASE_VERSION < tags.txt | --git BASE_REF' >&2
  exit 2
fi
export LC_ALL=C
current_tuple=$(parse_version "$current") || {
  echo "Invalid current version: $current" >&2
  exit 1
}
base_tuple=$(parse_version "$base") || {
  echo "Invalid base version: $base" >&2
  exit 1
}
read -r _ _ _ is_final _ <<<"$current_tuple"
if [[ $is_final == 1 && $(compare_versions "$current_tuple" "$base_tuple") == 0 ]]; then
  echo "Final version $current is already on the base; merge the next development bump first." >&2
  exit 1
fi
while IFS= read -r tag; do
  tag=${tag#v}
  tag=${tag#unstructured_}
  tuple=$(parse_version "$tag") || continue
  read -r _ _ _ tag_final _ <<<"$tuple"
  if [[ $is_final == 1 && $(compare_versions "$current_tuple" "$tuple") == 0 ]]; then
    echo "Final version $current already has a tag: $tag" >&2
    exit 1
  fi
  if [[ $is_final == 0 && $tag_final == 1 && $(compare_versions "$current_tuple" "$tuple") == -1 ]]; then
    echo "Development version $current is older than release tag $tag." >&2
    exit 1
  fi
done <<<"$tags"
echo "Version guard passed: $current (base $base)."
