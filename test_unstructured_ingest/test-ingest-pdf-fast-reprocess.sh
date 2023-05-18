#!/usr/bin/env bash
# A local connector to process pre-downloaded PDFs under `files-ingest-download` dir with --fast startegy

set -e

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/.. || exit 1


PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename,file_directory \
    --local-input-path files-ingest-download \
    --local-file-glob "*.pdf" \
    --structured-output-dir pdf-fast-reprocess-ingest-output \
    --partition-strategy fast \
    --reprocess \
    --num-processes 2

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp -r pdf-fast-reprocess-ingest-output test_unstructured_ingest/expected-structured-output/pdf-fast-reprocess/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/pdf-fast-reprocess pdf-fast-reprocess-ingest-output ; then

    echo
    echo "There are differences from the previously checked-in structured outputs."
    echo
    echo "If these differences are acceptable, overwrite by the fixtures by setting the env var:"
    echo
    echo "  export OVERWRITE_FIXTURES=true"
    echo
    echo "and then rerun this script."
    echo
    echo "NOTE: You'll likely just want to run scripts/ingest-test-fixtures-update.sh on x86_64 hardware"
    echo "to update fixtures for CI."
    echo
    exit 1

fi
