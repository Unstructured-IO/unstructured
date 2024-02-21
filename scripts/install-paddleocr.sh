#!/usr/bin/env bash

# aarch64 requires a custom build of paddlepaddle
if [ "${ARCH}" = "aarch64" ]; then
  python3 -m pip install unstructured.paddlepaddle
else
  python3 -m pip install paddlepaddle
fi
python3 -m pip install unstructured.paddleocr
