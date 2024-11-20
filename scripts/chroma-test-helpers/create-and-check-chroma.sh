#!/usr/bin/env bash

set -e

# $1 is the path for chroma to write the contents to. The symbol "&" runs process in background
python "$VIRTUAL_ENV/bin/chroma" run --path "$1" &
