#!/usr/bin/env bash

set -u

function usage {
  echo "Usage: $(basename "$0") [-c] -f FILE_TO_CHANGE REPLACEMENT_FORMAT [-f FILE_TO_CHANGE REPLACEMENT_FORMAT ...]" 2>&1
  echo 'Synchronize files to latest version in source file'
  echo '   -s              Specifies source file for version (default is CHANGELOG.md)'
  echo '   -f              Specifies a file to change and the format for searching and replacing versions'
  echo '                       FILE_TO_CHANGE is the file to be updated/checked for updates'
  echo '                       REPLACEMENT_FORMAT is one of (semver, release, api-release)'
  echo '                           semver indicates to look for a full semver version and replace with the latest full version'
  echo '                           release indicates to look for a release semver version (x.x.x) and replace with the latest release version'
  echo '                           api-release indicates to look for a release semver version in the context of an api route and replace with the latest release version'
  echo '   -c              Compare versions and output proposed changes without changing anything.'
}

function getopts-extra() {
  declare i=1
  # if the next argument is not an option, then append it to array OPTARG
  while [[ ${OPTIND} -le $# && ${!OPTIND:0:1} != '-' ]]; do
    OPTARG[i]=${!OPTIND}
    i+=1
    OPTIND+=1
  done
}

# Parse input options
declare CHECK=0
declare SOURCE_FILE="CHANGELOG.md"
declare -a FILES_TO_CHECK=()
declare -a REPLACEMENT_FORMATS=()
declare args
declare OPTIND OPTARG opt
while getopts ":hcs:f:" opt; do
  case $opt in
  h)
    usage
    exit 0
    ;;
  c)
    CHECK=1
    ;;
  s)
    SOURCE_FILE="$OPTARG"
    ;;
  f)
    getopts-extra "$@"
    args=("${OPTARG[@]}")
    # validate length of args, should be 2
    if [ ${#args[@]} -eq 2 ]; then
      FILES_TO_CHECK+=("${args[0]}")
      REPLACEMENT_FORMATS+=("${args[1]}")
    else
      echo "Exactly 2 arguments must follow -f option." >&2
      exit 1
    fi
    ;;
  \?)
    echo "Invalid option: -$OPTARG." >&2
    usage
    exit 1
    ;;
  esac
done

# Parse REPLACEMENT_FORMATS
RE_SEMVER_FULL="(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-((0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*))?(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?"
RE_RELEASE="(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
RE_API_RELEASE="v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
# Pull out semver appearing earliest in SOURCE_FILE.
LAST_VERSION=$(grep -o -m 1 -E "${RE_SEMVER_FULL}" "$SOURCE_FILE")
LAST_RELEASE=$(grep -o -m 1 -E "${RE_RELEASE}($|[^-+])" "$SOURCE_FILE" | grep -o -m 1 -E "${RE_RELEASE}")
LAST_API_RELEASE="v$(grep -o -m 1 -E "${RE_RELEASE}($|[^-+])$" "$SOURCE_FILE" | grep -o -m 1 -E "${RE_RELEASE}")"
declare -a RE_SEMVERS=()
declare -a UPDATED_VERSIONS=()
for i in "${!REPLACEMENT_FORMATS[@]}"; do
  REPLACEMENT_FORMAT=${REPLACEMENT_FORMATS[$i]}
  case $REPLACEMENT_FORMAT in
  semver)
    RE_SEMVERS+=("$RE_SEMVER_FULL")
    UPDATED_VERSIONS+=("$LAST_VERSION")
    ;;
  release)
    RE_SEMVERS+=("$RE_RELEASE")
    UPDATED_VERSIONS+=("$LAST_RELEASE")
    ;;
  api-release)
    RE_SEMVERS+=("$RE_API_RELEASE")
    UPDATED_VERSIONS+=("$LAST_API_RELEASE")
    ;;
  *)
    echo "Invalid replacement format: \"${REPLACEMENT_FORMAT}\". Use semver, release, or api-release" >&2
    exit 1
    ;;
  esac
done

if [ -z "$LAST_VERSION" ]; then
  # No match to semver regex in SOURCE_FILE, so no version to go from.
  printf "Error: Unable to find latest version from %s.\n" "$SOURCE_FILE"
  exit 1
fi

# Search files in FILES_TO_CHECK and change (or get diffs)
declare FAILED_CHECK=0

git fetch origin main
MAIN_VERSION=$(git show origin/main:unstructured/__version__.py | grep -o -m 1 -E "${RE_SEMVER_FULL}")
MAIN_IS_RELEASE=false
[[ $MAIN_VERSION != *"-dev"* ]] && MAIN_IS_RELEASE=true
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

for i in "${!FILES_TO_CHECK[@]}"; do
  FILE_TO_CHANGE=${FILES_TO_CHECK[$i]}
  RE_SEMVER=${RE_SEMVERS[$i]}
  UPDATED_VERSION=${UPDATED_VERSIONS[$i]}
  FILE_VERSION=$(grep -o -m 1 -E "${RE_SEMVER}" "$FILE_TO_CHANGE")

  if [ -z "$FILE_VERSION" ]; then
    # No match to semver regex in VERSIONFILE, so nothing to replace
    printf "Error: No semver version found in file %s.\n" "$FILE_TO_CHANGE"
    exit 1
  else
    if [[ "$MAIN_IS_RELEASE" == true && "$UPDATED_VERSION" == "$MAIN_VERSION" && "$CURRENT_BRANCH" != "main" ]]; then
      # Only one commit should be associated with a particular non-dev version
      if [[ "$CHECK" == 1 ]]; then
        printf "Error: there is already a commit associated with version %s.\n" "$MAIN_VERSION"
        exit 1
      else
        printf "Warning: there is already a commit associated with version %s.\n" "$MAIN_VERSION"
      fi
    fi

    # Replace semver in VERSIONFILE with semver obtained from SOURCE_FILE
    TMPFILE=$(mktemp /tmp/new_version.XXXXXX)
    # Check sed version, exit if version < 4.3
    if ! sed --version >/dev/null 2>&1; then
      CURRENT_VERSION=1.archaic
    else
      CURRENT_VERSION=$(sed --version | head -n1 | cut -d" " -f4)
    fi
    REQUIRED_VERSION="4.3"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$CURRENT_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
      echo "sed version must be >= ${REQUIRED_VERSION}" && exit 1
    fi
    sed -E -r "s/$RE_SEMVER/$UPDATED_VERSION/" "$FILE_TO_CHANGE" >"$TMPFILE"
    if [ $CHECK == 1 ]; then
      DIFF=$(diff "$FILE_TO_CHANGE" "$TMPFILE")
      if [ -z "$DIFF" ]; then
        printf "version sync would make no changes to %s.\n" "$FILE_TO_CHANGE"
        rm "$TMPFILE"
      else
        FAILED_CHECK=1
        printf "version sync would make the following changes to %s:\n%s\n" "$FILE_TO_CHANGE" "$DIFF"
        rm "$TMPFILE"
      fi
    else
      cp "$TMPFILE" "$FILE_TO_CHANGE"
      rm "$TMPFILE"
    fi
  fi
done

# Exit with code determined by whether changes were needed in a check.
if [ ${FAILED_CHECK} -ne 0 ]; then
  printf "\nVersions are out of sync! See above for diffs.\n"
  exit 1
else
  exit 0
fi
