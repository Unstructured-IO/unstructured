#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$CI" == "true" ]]; then
    if [ "$(( RANDOM % 10))" -lt 2 ] ; then
        # NOTE(crag): proper fix is being tracked here: https://github.com/Unstructured-IO/unstructured/issues/306
        echo "Skipping ingest 80% of github ingest tests to avoid rate limiting issue."
        exit 0
    fi
fi


PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --github-url dcneiner/Downloadify \
    --git-file-glob '*.html,*.txt' \
    --structured-output-dir github-downloadify-output \
    --verbose

if ! diff -ru test_unstructured_ingest/expected-structured-output/github-downloadify github-downloadify-output ; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo
   echo "If these differences are acceptable, copy the outputs from"
   echo "github-downloadify-output/ to test_unstructured_ingest/expected-structured-output/github-downloadify/ after running"
   echo
   echo "  PYTHONPATH=. ./unstructured/ingest/main.py --github-url dcneiner/Downloadify --github-file-glob '*.html,*.txt' --structured-output-dir github-downloadify-output --verbose"
   echo
   exit 1
fi
