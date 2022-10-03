#!/bin/bash
CHANGELOG_SEMVER="^((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-(?:(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?)$"
VERSION_SEMVER="(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-((0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?"
set -o pipefail
# Pull out most recent semver from CHANGELOG.md
LAST_VERSION=$(sed 's/#\+ //' CHANGELOG.md | grep -o -m 1 -E "${CHANGELOG_SEMVER}")
if [[ $LAST_VERSION ]];
then
	# Replace semver in __version__.py with semver obtained from CHANGELOG.md
	sed -i -r "s/$VERSION_SEMVER/$LAST_VERSION/" unstructured/__version__.py
fi
