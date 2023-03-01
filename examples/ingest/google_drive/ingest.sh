#!/usr/bin/env bash

# Processes the Unstructured-IO/unstructured repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in google-drive-ingest-output/

# NOTE, this script is not ready-to-run!
# You must enter a Drive ID and a Drive API Key before running.

# You can find out how to the API Key:
# https://support.google.com/googleapi/answer/6158862?hl=en
# The File or Folder ID can be gotten from the url of the file:
# https://drive.google.com/drive/folders/{folder-id}
# https://drive.google.com/file/d/{file-id}

# NOTE: Using the API Key only works when the file or folder is shared atleast with permission for
# "Anyone with the link" to view.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --drive-id "<file or folder id>" \
    --drive-api-key "<drive api key>" \
    --structured-output-dir google-drive-ingest-output \
    --num-processes 2 \
    --drive-recursive \
    --verbose

# Alternatively, you can call it using:
# unstructured-ingest --drive-id ...
