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

# Version appearing earliest in CHANGELOGFILE will be used as ground truth.
CHANGELOGFILE="CHANGELOG.md"
VERSIONFILE="unstructured/__version__.py"
RE_SEMVER_FULL="(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-((0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?"
# Pull out semver appearing earliest in CHANGELOGFILE.
LAST_VERSION=$(grep -o -m 1 -E "${RE_SEMVER_FULL}" "$CHANGELOGFILE")

if [ -z "$LAST_VERSION" ];
then
    # No match to semver regex in CHANGELOGFILE, so no version to go from.
    printf "Error: Unable to find latest version from %s.\n" "$CHANGELOGFILE"
    exit 1
fi

# Add files to this array that need to be kept in sync.
FILES_TO_CHANGE=("$VERSIONFILE")
# Add patterns to this array to be matched in the above files.
RE_SEMVERS=("$RE_SEMVER_FULL")
# Add versions to this array to be used as replacements for the patterns matched above from the corresponding files.
UPDATED_VERSIONS=("$LAST_VERSION")

for i in "${!FILES_TO_CHANGE[@]}"; do
    FILE_TO_CHANGE=${FILES_TO_CHANGE[$i]}
    RE_SEMVER=${RE_SEMVERS[$i]}
    UPDATED_VERSION=${UPDATED_VERSIONS[$i]}
    FILE_VERSION=$(grep -o -m 1 -E "${RE_SEMVER}" "$FILE_TO_CHANGE")
    if [ -z "$FILE_VERSION" ];
    then
        # No match to semver regex in VERSIONFILE, so nothing to replace
        printf "Error: No semver version found in file %s.\n" "$FILE_TO_CHANGE"
        exit 1
    else
        # Replace semver in VERSIONFILE with semver obtained from CHANGELOGFILE
        TMPFILE=$(mktemp /tmp/new_version.XXXXXX)
        sed -r "s/$RE_SEMVER/$UPDATED_VERSION/" "$FILE_TO_CHANGE" > "$TMPFILE"
        if [ $CHECK == 1 ];
        then
            DIFF=$(diff "$FILE_TO_CHANGE"  "$TMPFILE" )
            if [ -z "$DIFF" ];
            then
                printf "version sync would make no changes.\n"
                rm "$TMPFILE"
                exit 0
            else
                printf "version sync would make the following changes:\n%s\n" "$DIFF"
                rm "$TMPFILE"
                exit 1
            fi
        else
            cp "$TMPFILE" "$FILE_TO_CHANGE" 
            rm "$TMPFILE"
        fi
    fi
done