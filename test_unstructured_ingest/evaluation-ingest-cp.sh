#!/usr/bin/env bash

set -eu

SCRIPT_DIR=$(dirname "$(realpath "$0")")
cd "$SCRIPT_DIR"/.. || exit 1

EXPECTED_OUTPUTS_DIR=$1
CONNECTOR_TYPE=$2

EVAL_OUTPUT_ROOT=${EVAL_OUTPUT_ROOT:-$SCRIPT_DIR}
EVAL_OUTPUT_DIR=$EVAL_OUTPUT_ROOT/structured-output-eval/$CONNECTOR_TYPE

mkdir -p "$EVAL_OUTPUT_DIR"

while IFS= read -r json_filename; do
  if find "$EXPECTED_OUTPUTS_DIR" -name "$json_filename" -print -quit | grep -q .; then
    echo "evaluation: copying $json_filename to $EVAL_OUTPUT_DIR"
    find "$EXPECTED_OUTPUTS_DIR" -name "$json_filename" -exec cp {} "$EVAL_OUTPUT_DIR" \;
  fi
done <"$SCRIPT_DIR/metrics/metrics-json-manifest.txt"
