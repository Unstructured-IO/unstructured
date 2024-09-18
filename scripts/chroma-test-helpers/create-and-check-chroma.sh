#!/usr/bin/env bash

set -e

# $1 is the path for chroma to write the contents to. The symbol "&" runs process in background
echo "Current venv is:"
echo "$VIRTUAL_ENV"
echo "Current path is:"
echo "$PATH"
ls -l "$VIRTUAL_ENV/bin/chroma"
echo "================"
cat "$VIRTUAL_ENV/bin/chroma"
echo "================"
# chroma run --path "$1" &
python "$VIRTUAL_ENV/bin/chroma" run --path "$1" &
