#!/usr/bin/env bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR"/.. || exit 1

GH_READ_ONLY_ACCESS_TOKEN=${GH_READ_ONLY_ACCESS_TOKEN:-none}

ACCESS_TOKEN_FLAGS=""
# to update test fixtures, "export OVERWRITE_FIXTURES=true" and rerun this script
if [[ "$GH_READ_ONLY_ACCESS_TOKEN" != "none" ]]; then
   ACCESS_TOKEN_FLAGS="--git-access-token $GH_READ_ONLY_ACCESS_TOKEN"
elif [[ "$CI" == "true" ]]; then
    echo "Warning: GH_READ_ONLY_ACCESS_TOKEN is not defined in the CI environment."
    echo "This can lead to intermittent failures in test-ingest-github.sh, as non-auth'ed"
    echo "requests are severely rate limited by GitHub."
    echo
    if [ "$(( RANDOM % 10))" -lt 1 ] ; then
        # NOTE(crag): proper fix is being tracked here: https://github.com/Unstructured-IO/unstructured/issues/306
        echo "Skipping ingest 90% of github ingest tests to avoid rate limiting issue."
        exit 0
    fi
fi

#shellcheck disable=SC2086
PYTHONPATH=. ./unstructured/ingest/main.py \
    --metadata-exclude filename \
    --github-url dcneiner/Downloadify \
    --git-file-glob '*.html,*.txt' \
    --structured-output-dir github-downloadify-output \
    --reprocess \
    --preserve-downloads \
    --verbose $ACCESS_TOKEN_FLAGS

OVERWRITE_FIXTURES=${OVERWRITE_FIXTURES:-false}

set +e

# to update ingest test fixtures, run scripts/ingest-test-fixtures-update.sh on x86_64
if [[ "$OVERWRITE_FIXTURES" != "false" ]]; then

    cp github-downloadify-output/* test_unstructured_ingest/expected-structured-output/github-downloadify/

elif ! diff -ru test_unstructured_ingest/expected-structured-output/github-downloadify github-downloadify-output ; then
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
