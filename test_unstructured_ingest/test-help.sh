#!/usr/bin/env bash

set -u -o pipefail -e

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
sources=$(PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" --help | sed -e '1,/Commands/ d' | awk '{NF=1}1')
echo "Checking all source: $sources"
for src in $sources; do
  destinations=$(PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" "$src" --help | sed -e '1,/Destinations/ d' | awk '{NF=1}1')
  for dest in $destinations; do
    echo "Checking $src -> $dest"
    PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" "$src" "$dest" --help
  done
done
