#!/usr/bin/env bash

if [ "${ARCH}" = "aarch64" ]; then
		python3 -m pip install unstructured.paddlepaddle;
else
		python3 -m pip install paddlepaddle;
fi
python3 -m pip install paddleocr