#!/usr/bin/env bash

set -u -o pipefail -e

RUN_SCRIPT=${RUN_SCRIPT:-./unstructured/ingest/main.py}
sources=$(PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" --help | sed -e '1,/Commands/ d' | awk '{NF=1}1')
first_source=$(echo "$sources" | head -1)
destinations=$(PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" "$first_source" --help | sed -e '1,/Destinations/ d' | awk '{NF=1}1')
echo "Checking all source: $sources"
echo "Checking all destinations: $destinations"
for src in $sources; do
  for dest in $destinations; do
    echo "Checking $src -> $dest"
    PYTHONPATH=${PYTHONPATH:-.} "$RUN_SCRIPT" "$src" "$dest" --help
  done
done
