#!/usr/bin/env bash

# Processes all the issues in all projects within a jira domain, using the `unstructured` library.

# Structured outputs are stored in jira-ingest-output
SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/../../.. || exit 1

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
#     --> Space separated project ids or keys
# --list-of-boards
#     --> Space separated board ids or keys
# --list-of-issues
#     --> Space separated issue ids or keys

# Note: When any of the optional arguments are provided, connector will ingest only those components, and nothing else.
#       When none of the optional arguments are provided, all issues in all projects will be ingested.

PYTHONPATH=. ./unstructured/ingest/main.py \
  jira \
  --metadata-exclude filename,file_directory,metadata.data_source.date_processed \
  --url https://unstructured-jira-connector-test.atlassian.net \
  --user-email "$JIRA_USER_EMAIL" \
  --api-token "$JIRA_API_TOKEN" \
  --output-dir jira-ingest-output \
  --num-processes 2 \
  --reprocess
# --list-of-projects <your project keys/ids here (space separated)> \
# --list-of-boards <your board keys/ids here (space separated)> \
# --list-of-issues <your issue keys/ids here (space separated)> \
