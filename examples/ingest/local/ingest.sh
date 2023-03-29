***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes files in example-docs/ directory recursively
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in local-ingest-output/

***REMOVED*** To use the Local connector, the following is required:
***REMOVED***   1) --local-input-path  : path in the local file system which is to be processed
***REMOVED*** The following CLI args are optional:
***REMOVED***   2) --local-file-glob   : types of local files that are accepted,
***REMOVED***                            provided as a comma-separated list
***REMOVED***      Example: `--local-file-glob .docx` ensures only .docx files are processed.
***REMOVED***   3) --local-recursive   : if specified, the contents of sub-directories are processed as well

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --local-input-path example-docs \
    --structured-output-dir local-ingest-output \
    --num-processes 2 \
    --local-recursive \
    --verbose \

***REMOVED*** Alternatively, you can call it using:
***REMOVED*** unstructured-ingest --local-input-path ...
