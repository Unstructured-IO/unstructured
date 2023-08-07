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

LARGE_TABLE_BASE_ID="appQqieVsbxpwwD3i"
LARGE_TABLE_TABLE_ID="tbll85GCfxED1OrvC"
LARGE_BASE_BASE_ID="app8u2PSod8Mm9shf"
LARGE_WORKSPACE_BASE_ID_1="appSSCNWuIMjzeraO"
LARGE_WORKSPACE_BASE_ID_2="appyvCsaHWn38RzFc"
LARGE_WORKSPACE_BASE_ID_3="appbd8fkBv3AXj0Ab"
LARGE_WORKSPACE_BASE_ID_4="appHEvCPnpfiAwjPE"
LARGE_WORKSPACE_BASE_ID_5="appL9ND7LVWaItAmC"
LARGE_WORKSPACE_BASE_ID_6="appOGnidMsh93yCQI"
LARGE_WORKSPACE_BASE_ID_7="apps71HjvZRRgqHkz"
LARGE_WORKSPACE_BASE_ID_8="appvDbw5f7jCQqdsr"
LARGE_WORKSPACE_BASE_ID_9="appGFdtbLmqf2k8Ly"
LARGE_WORKSPACE_BASE_ID_10="appTn61bfU8vCIkGf"
LARGE_WORKSPACE_BASE_ID_11="app1c4CtIQ4ZToHIR"
LARGE_WORKSPACE_BASE_ID_12="apphvDFg6OC7l1xwo"
LARGE_TEST_LIST_OF_PATHS="$LARGE_BASE_BASE_ID $LARGE_TABLE_BASE_ID $LARGE_WORKSPACE_BASE_ID_1 $LARGE_WORKSPACE_BASE_ID_2 $LARGE_WORKSPACE_BASE_ID_3 $LARGE_WORKSPACE_BASE_ID_4 $LARGE_WORKSPACE_BASE_ID_5 $LARGE_WORKSPACE_BASE_ID_6 $LARGE_WORKSPACE_BASE_ID_7 $LARGE_WORKSPACE_BASE_ID_8 $LARGE_WORKSPACE_BASE_ID_9 $LARGE_WORKSPACE_BASE_ID_10 $LARGE_WORKSPACE_BASE_ID_11 $LARGE_WORKSPACE_BASE_ID_12"

PYTHONPATH=. ./unstructured/ingest/main.py \
    airtable \
    --download-dir "$DOWNLOAD_DIR" \
    --personal-access-token "$AIRTABLE_PERSONAL_ACCESS_TOKEN" \
    --list-of-paths "$LARGE_TEST_LIST_OF_PATHS" \
    --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.date \
    --num-processes 2 \
    --preserve-downloads \
    --reprocess \
    --structured-output-dir "$OUTPUT_DIR"



# We are expecting fifteen directories: fourteen bases and the parent directory
sh "$SCRIPT_DIR"/check-num-dirs-output.sh 15 "$OUTPUT_FOLDER_NAME"

# This test is not yet implemented. It is to ingest an Airtable base with a large number of tables
sh "$SCRIPT_DIR"/check-num-files-output.sh 1 "$OUTPUT_FOLDER_NAME"/"$LARGE_BASE_BASE_ID"/

# Test on ingesting a large number of bases
for i in {1..12}; do
  var="LARGE_WORKSPACE_BASE_ID_$i"
  sh "$SCRIPT_DIR"/check-num-files-output.sh 12 "$OUTPUT_FOLDER_NAME"/"${!var}"
done

# Test on ingesting a table with lots of rows
sh "$SCRIPT_DIR"/check-num-rows-and-columns-output.sh 39999 "$OUTPUT_DIR"/"$LARGE_TABLE_BASE_ID"/"$LARGE_TABLE_TABLE_ID".json
