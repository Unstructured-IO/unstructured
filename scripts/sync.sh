SEMVER="^((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$"
SEMVER="^((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-(?:(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?:[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?)$"
set -o pipefail
LASTVERSION="`cat CHANGELOG.md | sed 's/#\+ //' | grep -o -m 1 -E "${SEMVER}"`"
if [ -z "${VAR}" ];
then
	echo '__version__ = "'"$LASTVERSION"'"  # pragma: no cover' > unstructured/__version__.py
fi
