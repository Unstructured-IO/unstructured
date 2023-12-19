#!/usr/bin/env bash

set -eux

# Function to check if the current version is a non-dev version
function is_non_dev_version {
  local VERSION="$1"
  [[ "$VERSION" != *"-dev"* ]]
}

# Function to get the version from the current main branch
function get_main_branch_version {
  local VERSION
  git fetch origin main
  VERSION=$(git show origin/main:unstructured/__version__.py | grep -o -m 1 -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[a-zA-Z0-9.-]+)?")
  echo "$VERSION"
}

# Get the current version from the file
CURRENT_VERSION=$(grep -o -m 1 -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-dev[0-9]+)?" "unstructured/__version__.py")

# Check if the current version is a non-dev version and not matching the main version
if is_non_dev_version "$CURRENT_VERSION" && [ "$(get_main_branch_version)" != "$CURRENT_VERSION" ]; then
  echo "New release version: $CURRENT_VERSION"
fi
