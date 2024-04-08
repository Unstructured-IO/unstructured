#!/usr/bin/env bash

# For each dev commit to the main branch, there should be an individual changelog file
# that represents the changes made in that commit. In each release, all of the changelog files
# should be combined into a single file (CHANGELOG.md); then the individual changelog files should be removed.
# This script is used to test combine-changelogs functionality.

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR=$(dirname "$SCRIPT_DIR")
ASSETS_DIR=$SCRIPT_DIR/test_assets/test_combine_changelogs

python $PROJECT_DIR/scripts/changelogs/combine.py $ASSETS_DIR/changelogs-dev $ASSETS_DIR/test_CHANGELOG_do_not_update.md

# Check if the changelog was combined correctly
diff $ASSETS_DIR/test_CHANGELOG_do_not_update.md $ASSETS_DIR/expected_updated_CHANGELOG.md
git checkout $ASSETS_DIR/test_CHANGELOG_do_not_update.md