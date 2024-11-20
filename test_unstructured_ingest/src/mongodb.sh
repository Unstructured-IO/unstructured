#!/usr/bin/env bash

set -e

SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1
echo "SCRIPT_DIR: $SCRIPT_DIR"
OUTPUT_FOLDER_NAME=mongodb
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
SOURCE_MONGO_COLLECTION="sample-mongodb-data"
CI=${CI:-"false"}

if [ -z "$MONGODB_URI" ] && [ -z "$MONGODB_DATABASE_NAME" ]; then
  echo "Skipping MongoDB source ingest test because the MONGODB_URI and MONGODB_DATABASE_NAME env var are not set."
  exit 8
fi

# NOTE(robinson) - per pymongo docs, pymongo ships with its own version of the bson library,
# which is incompatible with the bson installed from pypi. bson is installed as part of the
# astradb dependencies.
# ref: https://pymongo.readthedocs.io/en/stable/installation.html
python -m pip uninstall -y bson pymongo
pip install "unstructured-ingest[mongodb]"

RUN_SCRIPT=${RUN_SCRIPT:-unstructured-ingest}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  mongodb \
  --metadata-exclude file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.date_created,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --download-dir "$DOWNLOAD_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --uri "$MONGODB_URI" \
  --database "$MONGODB_DATABASE_NAME" \
  --collection "$SOURCE_MONGO_COLLECTION" \
  --work-dir "$WORK_DIR" \
  --preserve-downloads \
  --reprocess \
  --batch-size 2 \
  --verbose

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
