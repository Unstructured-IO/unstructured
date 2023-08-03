#!/usr/bin/env bash
set -e

# Description: This test checks if the number of bases and tables processed are as expected.
# Each base shows up as a directory in the output folder, hence check-num-dirs-output.sh
# Each table shows up as a file in a base directory, hence check-num-files-output.sh

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=airtable-large
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME

if [ -z "$AIRTABLE_PERSONAL_ACCESS_TOKEN" ]; then
   echo "Skipping Airtable ingest test because the AIRTABLE_PERSONAL_ACCESS_TOKEN is not set."
   exit 0
fi

PYTHONPATH=. ./unstructured/ingest/main.py \
    --download-dir "$DOWNLOAD_DIR" \
    --airtable-personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
    --airtable-list-of-paths "$LARGE_TEST_LIST_OF_PATHS" \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.date \
    --num-processes 2 \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"



# We are expecting two directories: one for the space, and one is the output directory itself
# Example:
# Output dir: unstructured/test_unstructured_ingest/structured-output/confluence-large
# Space dir: unstructured/test_unstructured_ingest/structured-output/confluence-large/testteamsp1
sh "$SCRIPT_DIR"/check-num-dirs-output.sh 14 "$OUTPUT_FOLDER_NAME"

# We are expecting 250 files due to the --confluence-num-of-docs-from-each-space 250 that we provided.
sh "$SCRIPT_DIR"/check-num-files-output.sh 1 "$OUTPUT_FOLDER_NAME"/"$LARGE_BASE_BASE_ID"/

for i in {1..12}; do
  var="LARGE_WORKSPACE_BASE_ID_$i"
  sh "$SCRIPT_DIR"/check-num-files-output.sh 12 "$OUTPUT_FOLDER_NAME"/"${!var}"
done
