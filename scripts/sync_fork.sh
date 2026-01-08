#!/bin/bash

# Simple script to recreate a fork branch as a new branch in the current repository
# Usage: ./sync_fork.sh <fork_url> <fork_branch>

set -e

if [ $# -ne 2 ]; then
  echo "Usage: $0 <fork_url> <fork_branch>"
  echo "Example: $0 https://github.com/user/fork.git feature-branch"
  exit 1
fi

FORK_URL="$1"
FORK_BRANCH="$2"

echo "Adding fork as remote..."
git remote add fork "$FORK_URL" 2>/dev/null || git remote set-url fork "$FORK_URL"

echo "Fetching fork..."
git fetch fork

echo "Creating new branch '$FORK_BRANCH' with fork's changes..."
git checkout -b "$FORK_BRANCH" "fork/$FORK_BRANCH"

echo "Removing fork remote..."
git remote remove fork

echo "Done! You're now on branch '$FORK_BRANCH' with the fork's changes. Fork remote has been removed."
