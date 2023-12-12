#!/usr/bin/env bash

set -e

# $1 is first argument passed to shell. & runs process in background
chroma run --path "$1" &
