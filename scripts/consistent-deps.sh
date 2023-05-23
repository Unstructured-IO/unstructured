#!/usr/bin/env bash

function join_by {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

excludefiles=("requirements/build.txt")

shopt -s nullglob
reqfiles=(requirements/*.txt)

for excludefile in "${excludefiles[@]}"; do
  for i in "${!reqfiles[@]}"; do
    if [[ ${reqfiles[i]} = "$excludefile" ]]; then
      unset 'reqfiles[i]'
    fi
  done
done


reqstring=$(join_by ' -r ' "${reqfiles[@]}")
reqstring="-r ${reqstring}"

pipcommand="pip install --dry-run --ignore-installed ${reqstring}"
$pipcommand >> /dev/null
