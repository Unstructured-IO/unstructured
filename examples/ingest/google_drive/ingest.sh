#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in google-drive-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a Drive ID and a Drive Service Account Key before running.

# You can find out how to the Service account Key:
# https://developers.google.com/workspace/guides/create-credentials#service-account

# The File or Folder ID can be gotten from the url of the file, such as:
# https://drive.google.com/drive/folders/{folder-id}
# https://drive.google.com/file/d/{file-id}

# NOTE: Using the Service Account key only works when the file or folder
# is shared atleast with permission for "Anyone with the link" to view
# OR the email address for the service account is given access to the file
# or folder.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  google-drive \
  --drive-id "<file or folder id>" \
  --service-account-key "<path to drive service account key>" \
  --output-dir google-drive-ingest-output \
  --num-processes 2 \
  --recursive \
  --verbose
#    --extension ".docx" # Ensures only .docx files are processed.

# Alternatively, you can call it using:
# unstructured-ingest gdrive --drive-id ...
