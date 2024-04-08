#!/usr/bin/env bash

# For each dev commit to the main branch, there should be an individual changelog file
# that represents the changes made in that commit. In each release, all of the changelog files
# should be combined into a single file (CHANGELOG.md); then the individual changelog files should be removed.
# This script is used to remove the individual changelog files.
# The script takes the changelogs-dev directory as an argument.

# Allows extended patterns on rm
shopt -s extglob

SCRIPT_DIR=$(dirname "$(realpath "$0")")
PROJECT_DIR=$(dirname $(dirname "$SCRIPT_DIR"))

rm $PROJECT_DIR/$1/!(dev-changelog-template.md)