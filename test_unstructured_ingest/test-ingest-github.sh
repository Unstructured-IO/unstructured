#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

if [[ "$CI" == "true" && "$(( RANDOM % 10))" != "1" ]]; then
    # NOTE(crag): proper fix is being tracked here: https://github.com/Unstructured-IO/unstructured/issues/306
    echo "Skipping ingest 90% of github ingest tests to avoid rate limiting issue."
    exit 0
fi


PYTHONPATH=. ./unstructured/ingest/main.py --github-url dcneiner/Downloadify --github-file-glob '*.html,*.txt' --structured-output-dir github-downloadify-output --verbose

if ! diff -ru github-downloadify-output test_unstructured_ingest/expected-structured-output/github-downloadify ; then
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
