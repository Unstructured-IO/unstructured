#!/usr/bin/env bash

# aarch64 requires a custom build of paddlepaddle
if [ "${ARCH}" = "aarch64" ]; then
		python3 -m pip install unstructured.paddlepaddle;
else
		python3 -m pip install paddlepaddle;
fi
python3 -m pip install unstructured.paddleocr

# Note(yuming): Disable signal handlers at C++ level upon failing
# ref: https://www.paddlepaddle.org.cn/documentation/docs/en/api/paddle/disable_signal_handler_en.html#disable-signal-handler
# this is mainly for the paddle instance used by layourparser
# ref: https://github.com/Layout-Parser/layout-parser/blob/main/src/layoutparser/models/paddledetection/layoutmodel.py#L31
python3 -c "import paddle; paddle.disable_signal_handler()"
