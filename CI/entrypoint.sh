#!/usr/bin/env bash

cd /unstructured || exit
source .venv/bin/activate
./test_unstructured_ingest/test-ingest.sh
