#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py --github-url dcneiner/Downloadify --github-file-glob '*.html,*.txt' --structured-output-dir github-downloadify-output --verbose

if ! diff -ru github-downloadify-output test_unstructured_ingest/expected-structured-output/github-downloadify ; then
   echo
   echo "There are differences from the previously checked-in structured outputs."
   echo 
   echo "If these differences are acceptable, copy the outputs from"
   echo "s3-small-batch-output/ to test_unstructured_ingest/expected-structured-output/s3-small-batch/ after running"
   echo 
   echo "  PYTHONPATH=. python examples/ingest/s3-small-batch/main.py --structured-output-dir s3-small-batch-output"
   echo
   exit 1
fi
