#!/usr/bin/env bash

####################################################################################################
# Check depedency consistency by forcing pip to resolve all the requirement .txt files at once
# (without installing).
####################################################################################################

echo "Checking consistency of dependencies..."

# Joins an array of strings using the specified delimiter.
function join_by {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

# NOTE(alan): Add any dependency files here we don't want to include in the resolution.
excludefiles=("requirements/build.txt")

# Build an array of requirements files.
shopt -s nullglob
reqfiles=(requirements/*.txt)

# Remove the excluded files from the array of requirements files.
for excludefile in "${excludefiles[@]}"; do
  for i in "${!reqfiles[@]}"; do
    if [[ ${reqfiles[i]} = "$excludefile" ]]; then
      unset 'reqfiles[i]'
    fi
  done
done

# Turn the requirement files array into pip -r flags.
reqstring=$(join_by ' -r ' "${reqfiles[@]}")
reqstring="-r ${reqstring}"

# This pip command will attempt to resolve the dependencies without installing anything.
pipcommand="pip install --dry-run --ignore-installed ${reqstring}"
if $pipcommand >>/dev/null; then
  echo "Everything looks fine!"
else
  exit 1
fi
