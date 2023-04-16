#!/usr/bin/env bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --gitlab-url https://gitlab.com/gitlab-com/content-sites/docsy-gitlab \
    --git-file-glob '*.md,*.txt' \
    --structured-output-dir gitlab-ingest-output \
    --git-branch 'v0.0.7' \
    --verbose

set +e

if [ "$(find 'gitlab-ingest-output' -type f -printf '.' | wc -c)" != 2 ]; then
   echo
   echo "2 files should have been created."
   exit 1
fi
