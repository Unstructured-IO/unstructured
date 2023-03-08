***REMOVED***!/usr/bin/env bash

***REMOVED*** Processes the arbitrarily chosen https://gitlab.com/gitlab-com/content-sites/docsy-gitlab repository
***REMOVED*** through Unstructured's library in 2 processes.

***REMOVED*** Structured outputs are stored in gitlab-ingest-output/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --gitlab-url https://gitlab.com/gitlab-com/content-sites/docsy-gitlab \
    --git-branch 'v0.0.7' \
    --structured-output-dir gitlab-ingest-output \
    --num-processes 2 \
    --verbose

***REMOVED*** Alternatively, you can call it using:
***REMOVED*** unstructured-ingest --gitlab-url ...
