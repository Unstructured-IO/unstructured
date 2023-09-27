#!/usr/bin/env bash
set -e

# Description: This test checks if all the processed content is the same as the expected outputs
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

OUTPUT_FOLDER_NAME=jira-diff
OUTPUT_DIR=$SCRIPT_DIR/structured-output/$OUTPUT_FOLDER_NAME
DOWNLOAD_DIR=$SCRIPT_DIR/download/$OUTPUT_FOLDER_NAME
max_processes=${MAX_PROCESSES:=$(python -c "import os; print(os.cpu_count())")}

# shellcheck disable=SC1091
source "$SCRIPT_DIR"/cleanup.sh
trap 'cleanup_dir "$OUTPUT_DIR"' EXIT

if [ -z "$JIRA_INGEST_USER_EMAIL" ] || [ -z "$JIRA_INGEST_API_TOKEN" ]; then
   echo "Skipping Jira ingest test because the JIRA_INGEST_USER_EMAIL or JIRA_INGEST_API_TOKEN env var is not set."
   exit 0
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

PYTHONPATH=. ./unstructured/ingest/main.py \
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
        --issues "JCTP2-4,JCTP2-7,JCTP2-8,10012,JCTP2-11"



"$SCRIPT_DIR"/check-diff-expected-output.sh $OUTPUT_FOLDER_NAME
