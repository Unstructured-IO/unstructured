***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes the Unstructured-IO/unstructured repository
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in google-drive-ingest-output/

***REMOVED*** NOTE, this script is not ready-to-run!
***REMOVED*** You must enter a Drive ID and a Drive Service Account Key before running.

***REMOVED*** You can find out how to the Service account Key:
***REMOVED*** https://developers.google.com/workspace/guides/create-credentials***REMOVED***service-account

***REMOVED*** The File or Folder ID can be gotten from the url of the file, such as:
***REMOVED*** https://drive.google.com/drive/folders/{folder-id}
***REMOVED*** https://drive.google.com/file/d/{file-id}

***REMOVED*** NOTE: Using the Service Account key only works when the file or folder
***REMOVED*** is shared atleast with permission for "Anyone with the link" to view
***REMOVED*** OR the email address for the service account is given access to the file
***REMOVED*** or folder.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --drive-id "<file or folder id>" \
    --drive-service-account-key "<path to drive service account key>" \
    --structured-output-dir google-drive-ingest-output \
    --num-processes 2 \
    --drive-recursive \
    --verbose \
***REMOVED***    --extension ".docx" ***REMOVED*** Ensures only .docx files are processed.

***REMOVED*** Alternatively, you can call it using:
***REMOVED*** unstructured-ingest --drive-id ...
