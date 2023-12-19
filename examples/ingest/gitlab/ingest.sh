#!/usr/bin/env bash

# Processes the arbitrarily chosen https://gitlab.com/gitlab-com/content-sites/docsy-gitlab repository
# through Unstructured's library in 2 processes.

# Structured outputs are stored in gitlab-ingest-output/

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
cd "$SCRIPT_DIR"/../../.. || exit 1

PYTHONPATH=. ./unstructured/ingest/main.py \
  gitlab \
  --url https://gitlab.com/gitlab-com/content-sites/docsy-gitlab \
  --git-branch 'v0.0.7' \
  --output-dir gitlab-ingest-output \
  --num-processes 2 \
  --verbose

# Alternatively, you can call it using:
# unstructured-ingest gitlab --gitlab-url ...
