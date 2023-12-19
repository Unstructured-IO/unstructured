#!/usr/bin/env bash
set -e

# Description: This test checks if all the processed content is the same as the expected outputs
SRC_PATH=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$SRC_PATH")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=jira-diff
OUTPUT_ROOT=${OUTPUT_ROOT:-$SCRIPT_DIR}
OUTPUT_DIR=$OUTPUT_ROOT/structured-output/$OUTPUT_FOLDER_NAME
WORK_DIR=$OUTPUT_ROOT/workdir/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$OUTPUT_ROOT/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python3 -c "import os; print(os.cpu_count())")}
CI=${CI:-"false"}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
function cleanup() {
  cleanup_dir "$OUTPUT_DIR"
  cleanup_dir "$WORK_DIR"
  if [ "$CI" == "true" ]; then
    cleanup_dir "$DOWNLOAD_DIR"
  fi
}
trap cleanup EXIT

if [ -z "$JIRA_INGEST_USER_EMAIL" ] || [ -z "$JIRA_INGEST_API_TOKEN" ]; then
  echo "Skipping Jira ingest test because the JIRA_INGEST_USER_EMAIL or JIRA_INGEST_API_TOKEN env var is not set."
  exit 8
fi

# Required arguments:
# --url
#   --> Atlassian (Jira) domain URL
# --api-token
#   --> Api token to authenticate into Atlassian (Jira).
#       Check https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/ for more info.
# --user-email
#   --> User email for the domain, such as xyz@unstructured.io

# Optional arguments:
# --list-of-projects
#     --> Comma separated project ids or keys
# --list-of-boards
#     --> Comma separated board ids or keys
# --list-of-issues
#     --> Comma separated issue ids or keys

# Note: When any of the optional arguments are provided, connector will ingest only those components, and nothing else.
#       When none of the optional arguments are provided, all issues in all projects will be ingested.

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" \
  jira \
  --download-dir "$DOWNLOAD_DIR" \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed,metadata.last_modified,metadata.detection_class_prob,metadata.parent_id,metadata.category_depth \
  --num-processes "$max_processes" \
  --preserve-downloads \
  --reprocess \
  --output-dir "$OUTPUT_DIR" \
  --verbose \
  --url https://unstructured-jira-connector-test.atlassian.net \
  --user-email "$JIRA_INGEST_USER_EMAIL" \
  --api-token "$JIRA_INGEST_API_TOKEN" \
  --projects "JCTP3" \
  --boards "1" \
  --issues "JCTP2-4,JCTP2-7,JCTP2-8,10012,JCTP2-11" \
  --work-dir "$WORK_DIR"

"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
