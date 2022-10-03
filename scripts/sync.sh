#!/bin/bash
SEMVER="^((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$"
SEMVER="^((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-(?:(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?)$"
set -o pipefail
LASTVERSION=$(sed 's/#\+ //' CHANGELOG.md | grep -o -m 1 -E "${SEMVER}")
if [[ $LASTVERSION ]];
then
	echo '__version__ = "'"$LASTVERSION"'"  # pragma: no cover' > unstructured/__version__.py
fi
