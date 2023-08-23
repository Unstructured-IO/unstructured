#!/usr/bin/env bash

# Description: 
#
# Arguments:
#   $1 folder with json files to process
#   $2 folder to place the text field for all entries, for all files at $1
 
set +e

INPUT_FOLDER_NAME=$1
OUTPUT_DIR_TEXT=$2
mkdir -p "$OUTPUT_DIR_TEXT"
find "$INPUT_FOLDER_NAME" -type f -print0| xargs -n1 "jq '.[].text'<{}>$OUTPUT_DIR_TEXT" \;