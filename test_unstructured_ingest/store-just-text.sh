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
echo script_dir $SCRIPT_DIR
mkdir -p $OUTPUT_DIR_TEXT
find $INPUT_FOLDER_NAME -type f -exec bash -c '$1/clean.sh {} $2' bash $SCRIPT_DIR $OUTPUT_DIR_TEXT \;