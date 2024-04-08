#!/usr/bin/env bash

# Get the current branch name, replace all slashes with dashes,
# and create a markdown file with the branch name.
# This script is to for create dev changelog files for dev PRs.

branch_name=$(git rev-parse --abbrev-ref HEAD)
modified_branch_name=$(echo "$branch_name" | sed 's/\//-/g')
dev_changelog_name=$modified_branch_name.md
cp changelogs-dev/dev-changelog-template.md "changelogs-dev/$dev_changelog_name"