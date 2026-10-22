#!/usr/bin/env bash
# Usage: check-new-release-version.sh [merge-version base-version [tags-file]]
# Without arguments, read HEAD and VERSION_BASE_REF (default origin/main).
set -euo pipefail

# Canonical numeric fields, with a dev flag and number. Avoid machine-integer
# overflow by comparing decimal strings rather than shell arithmetic on versions.
parse_version() {
  local value=$1 field
  value=${value#unstructured_}
  value=${value#v}
  [[ $value =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)((-dev|\.dev)([0-9]*))?$ ]] || return 1
  PARTS=("${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}" "${BASH_REMATCH[6]:-0}")
  if [[ -n ${PARTS[3]} ]]; then PARTS[3]=0; else PARTS[3]=1; fi
  for field in 0 1 2 4; do
    while [[ ${#PARTS[field]} -gt 1 && ${PARTS[field]} == 0* ]]; do
      PARTS[field]=${PARTS[field]#0}
    done
  done
}

# Return success for left < right. All inputs are canonical decimal strings.
version_less() {
  local left=$1 right=$2 i
  local -a a b
  parse_version "$left"
  a=("${PARTS[@]}")
  parse_version "$right"
  b=("${PARTS[@]}")
  for i in 0 1 2 3 4; do
    if [[ ${#a[i]} -lt ${#b[i]} ]]; then return 0; fi
    if [[ ${#a[i]} -gt ${#b[i]} ]]; then return 1; fi
    if [[ ${a[i]} < ${b[i]} ]]; then return 0; fi
    if [[ ${a[i]} > ${b[i]} ]]; then return 1; fi
  done
  return 1
}

read_version() {
  local source line
  source=$(git show "$1:unstructured/__version__.py") || return 1
  while IFS= read -r line; do
    if [[ $line =~ ^__version__[[:space:]]*=[[:space:]]*[\"\']([^\"\']+)[\"\'] ]]; then
      printf '%s\n' "${BASH_REMATCH[1]}"
      return 0
    fi
  done <<<"$source"
  echo "Cannot read version at $1" >&2
  return 1
}

main() {
  local current base normalized_current normalized_base dev tags tag latest=''
  local -a PARTS
  if [[ $# == 0 ]]; then
    current=$(read_version HEAD)
    base=$(read_version "${VERSION_BASE_REF:-origin/main}")
  elif [[ $# == 2 || $# == 3 ]]; then
    current=$1
    base=$2
  else
    echo 'Usage: check-new-release-version.sh [merge-version base-version [tags-file]]' >&2
    return 2
  fi
  parse_version "$current" || {
    echo "Invalid merge version: $current" >&2
    return 1
  }
  normalized_current="${PARTS[*]}"
  dev=${PARTS[3]}
  parse_version "$base" || {
    echo "Invalid base version: $base" >&2
    return 1
  }
  normalized_base="${PARTS[*]}"
  if [[ $normalized_current == "$normalized_base" ]]; then
    if [[ $dev == 0 ]]; then
      echo "PASS: unchanged development version $current (no tag lookup)."
      return 0
    fi
    echo 'FAIL: main (or the release PR ahead in the queue) holds a release version; the next -dev bump must land first.' >&2
    return 1
  fi

  if [[ $# == 3 ]]; then
    tags=$(cat "$3")
  else
    # Only names are needed; avoid downloading tagged commits and history.
    tags=$(git ls-remote --tags --refs origin | cut -f2)
    tags=${tags//refs\/tags\//}
  fi
  while IFS= read -r tag; do
    parse_version "$tag" || continue
    if [[ $dev == 1 && ${PARTS[*]} == "$normalized_current" ]]; then
      echo "FAIL: release version $current is already tagged as $tag." >&2
      return 1
    fi
    [[ ${PARTS[3]} == 1 ]] || continue
    if [[ -z $latest ]] || version_less "$latest" "$tag"; then latest=$tag; fi
  done <<<"$tags"
  if [[ $dev == 0 && -n $latest ]] && version_less "$current" "$latest"; then
    echo "FAIL: development version $current is below latest release tag $latest." >&2
    return 1
  fi
  echo "PASS: version change $base -> $current."
}

main "$@"
