#!/usr/bin/env bash

set -euo pipefail

handle_error() {
    if [ -d "unstructured-api" ]; then
        rm -rf unstructured-api
    fi
    exit 1
}

trap 'handle_error' EXIT

git clone https://github.com/Unstructured-IO/unstructured-api.git --depth 1
cd unstructured-api && make install && cd ../
make install-project-local
cd unstructured-api && make test && cd ../
rm -rf unstructured-api
