"""Benchmark for YoloX image_processing() memory optimization.

Uses a fake ONNX session to isolate the memory behavior of image_processing()
without requiring the real model weights. The fake session allocates a realistic
35 MiB workspace to simulate ONNX inference memory pressure.
"""

import numpy as np
from PIL import Image as PILImage

from unstructured_inference.models.yolox import UnstructuredYoloXModel


class _FakeInput:
    def __init__(self) -> None:
        self.name = "input"


class _FakeSession:
    """Simulates an ONNX inference session with realistic memory allocation."""

    def get_inputs(self):
        return [_FakeInput()]

    def run(self, _names, _inputs):
        workspace = np.empty((35 * 1024 * 1024,), dtype=np.uint8)  # 35 MiB  # noqa: F841
        # input_shape (1024,768), strides [8,16,32] → 128*96 + 64*48 + 32*24 = 16128
        return [np.random.randn(1, 16128, 16).astype(np.float32)]


def make_model() -> UnstructuredYoloXModel:
    model = object.__new__(UnstructuredYoloXModel)
    model.model = _FakeSession()
    model.model_path = "yolox_fake"
    model.layout_classes = {
        0: "Caption",
        1: "Footnote",
        2: "Formula",
        3: "List-item",
        4: "Page-footer",
        5: "Page-header",
        6: "Picture",
        7: "Section-header",
        8: "Table",
        9: "Text",
        10: "Title",
    }
    return model


# Letter-size page at 200 DPI — the default render resolution
def make_letter_200dpi() -> PILImage.Image:
    return PILImage.fromarray(np.random.randint(0, 255, (2200, 1700, 3), dtype=np.uint8))


def run_image_processing():
    model = make_model()
    img = make_letter_200dpi()
    return model.image_processing(img)


def test_benchmark_yolox_image_processing(benchmark):
    benchmark(run_image_processing)
