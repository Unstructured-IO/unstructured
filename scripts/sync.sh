#!/bin/bash
SEMVER="(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-((0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?"
# Pull out semver appearing earliest in CHANGELOG.md
LAST_VERSION=$(grep -o -m 1 -E "${SEMVER}" CHANGELOG.md)
if [[ $LAST_VERSION ]];
then
	# Replace semver in __version__.py with semver obtained from CHANGELOG.md
	sed -i -r "s/$SEMVER/$LAST_VERSION/" unstructured/__version__.py
fi
