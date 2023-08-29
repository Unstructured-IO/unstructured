#!/usr/bin/env bash

# Description: 
#
# Arguments:
#   $1 folder with json files to process
#   $2 folder to place the text field for all entries, for all files at $1
 
set +e
SCRIPT_DIR=$(dirname "$(realpath "$0")")
INPUT_FOLDER_NAME=$1
OUTPUT_DIR_TEXT=$2
echo "INPUT FOLDER: $INPUT_FOLDER_NAME"
echo "OUTPUT FOLDER: $OUTPUT_DIR_TEXT"
mkdir -p "$OUTPUT_DIR_TEXT"
find "$INPUT_FOLDER_NAME" -type f -print0| xargs -IX --null -n1 "$SCRIPT_DIR"/json-to-text.sh X "$OUTPUT_DIR_TEXT"
