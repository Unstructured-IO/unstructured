#!/usr/bin/env bash

set -e

# $1 is the path for chroma to write the contents to. The symbol "&" runs process in background
chroma run --path "$1" &
