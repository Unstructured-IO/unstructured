#!/usr/bin/env bash

set -e

# Function to check if the current version is a non-dev version
function is_non_dev_version {
    local VERSION="$1"
    [[ "$VERSION" != *"-dev"* ]]
}

# Function to get the version from the current main branch
function get_main_branch_version {
    local VERSION
    VERSION=$(git show origin/main:unstructured/__version__.py | grep -o -m 1 -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
    echo "$VERSION"
}

# Get the current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Get the current version from the file
CURRENT_VERSION=$(grep -o -m 1 -E "(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-dev[0-9]+)?" "unstructured/__version__.py")

# Check if the current version is a non-dev version and not matching the main version
if is_non_dev_version "$CURRENT_VERSION"; then
    MAIN_VERSION=$(get_main_branch_version)
    if [ "$MAIN_VERSION" != "$CURRENT_VERSION" ]; then
        echo "Current version $CURRENT_VERSION is a non-dev version and does not match the version in the main branch ($MAIN_VERSION)."
        exit 1  # Exit with a non-zero status code
    fi
fi
