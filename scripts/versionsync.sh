#!/bin/bash

CHECK=0
while getopts ":c" opt; do
  case $opt in
    c)
      CHECK=1
      ;;
    \?)
      echo "Invalid option: -$OPTARG. Use -c to show changes without applying, use no options to apply changes." >&2
      exit 1
      ;;
  esac
done

CHANGELOGFILE="CHANGELOG.md"
VERSIONFILE="unstructured/__version__.py"
SEMVER="(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-((0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?"
# Pull out semver appearing earliest in CHANGELOGFILE
LAST_VERSION=$(grep -o -m 1 -E "${SEMVER}" "$CHANGELOGFILE")
CURR_VERSION=$(grep -o -m 1 -E "${SEMVER}" "$VERSIONFILE")
if [ -z $CURR_VERSION ];
then
	# No match to semver regex in VERSIONFILE, so nothing to replace
	printf "Error: No semver version found in file $VERSIONFILE.\n";
	exit 1;
fi
if [ -z $LAST_VERSION ];
then
	# No match to semver regex in CHANGELOGFILE, so no version to go from
	printf "Error: Unable to find latest version from $CHANGELOGFILE.\n"
	exit 1
else
	# Replace semver in VERSIONFILE with semver obtained from CHANGELOGFILE
	TMPFILE=$(mktemp /tmp/new_version.XXXXXX)
	sed -r "s/$SEMVER/$LAST_VERSION/" "$VERSIONFILE" > "$TMPFILE"
	DIFF=$(diff "$VERSIONFILE"  "$TMPFILE" )
	if [ $CHECK == 1 ];
	then
		if [ -z "$DIFF" ];
		then
			printf "verion sync would make no changes.\n";
			rm "$TMPFILE"
			exit 0;
		else
			printf "version sync would make the following changes:\n$DIFF\n";
			rm "$TMPFILE"
			exit 1;
		fi
	else
		cp "$TMPFILE" "$VERSIONFILE" 
		rm "$TMPFILE"
	fi
fi
