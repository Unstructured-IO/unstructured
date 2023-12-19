#!/usr/bin/env bash

# Description: Delete (cleanup) permissions files in a folder, so that they are not included in
#              text diff tests.
#
# Arguments:
#   - $1: Name of the folder to do the cleanup operation in.

set +e
if [ "$#" -ne 1 ]; then
  echo "Please provide a folder to clean the files in: $0 <folder_path>"
  exit 1
fi

folder_path="$1"
if [ ! -d "$folder_path" ]; then
  echo "'$folder_path' is not a directory. Please provide a folder / directory."
  exit 1
fi

for file in "$folder_path"/*_SEP_*; do
  if [ -e "$file" ]; then
    rm "$file"
  fi
done

echo "Completed cleanup for permissions files"
