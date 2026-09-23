import os
from unittest.mock import patch

import pytest
from PIL import Image

import unstructured_inference.models.base as models
import unstructured_inference.models.detectron2onnx as detectron2


class MockDetectron2ONNXLayoutModel:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def run(self, *args):
        return ([(1, 2, 3, 4)], [0], [(4, 5)], [0.818])

    def get_inputs(self):
        class input_thing:
            name = "Bernard"

        return [input_thing()]


def test_load_default_model(monkeypatch):
    monkeypatch.setattr(models, "models", {})
    with patch.object(
        detectron2.onnxruntime,
        "InferenceSession",
        new=MockDetectron2ONNXLayoutModel,
    ):
        model = models.get_model("detectron2_mask_rcnn")

    assert isinstance(model.model, MockDetectron2ONNXLayoutModel)


@pytest.mark.parametrize(("model_path", "label_map"), [("asdf", "diufs"), ("dfaw", "hfhfhfh")])
def test_load_model(model_path, label_map):
    with patch.object(detectron2.onnxruntime, "InferenceSession", return_value=True):
        model = detectron2.UnstructuredDetectronONNXModel()
        model.initialize(model_path=model_path, label_map=label_map)
        args, _ = detectron2.onnxruntime.InferenceSession.call_args
        assert args == (model_path,)
    assert label_map == model.label_map


def test_unstructured_detectron_model():
    model = detectron2.UnstructuredDetectronONNXModel()
    model.model = 1
    with patch.object(detectron2.UnstructuredDetectronONNXModel, "predict", return_value=[]):
        result = model(None)
    assert isinstance(result, list)
    assert len(result) == 0


def test_inference():
    with patch.object(
        detectron2.onnxruntime,
        "InferenceSession",
        return_value=MockDetectron2ONNXLayoutModel(),
    ):
        model = detectron2.UnstructuredDetectronONNXModel()
        model.initialize(model_path="test_path", label_map={0: "test_class"})
        assert isinstance(model.model, MockDetectron2ONNXLayoutModel)
        with open(os.path.join("sample-docs", "receipt-sample.jpg"), mode="rb") as fp:
            image = Image.open(fp)
            image.load()
        elements = model(image)
        assert len(elements) == 1
        element = elements[0]
        (x1, y1), _, (x2, y2), _ = element.bbox.coordinates
        assert hasattr(
            element,
            "prob",
        )  # NOTE(pravin) New Assertion to Make Sure element has probabilities
        assert isinstance(
            element.prob,
            float,
        )  # NOTE(pravin) New Assertion to Make Sure Populated Probability is Float
        # NOTE(alan): The bbox coordinates get resized, so check their relative proportions
        assert x2 / x1 == pytest.approx(3.0)  # x1 == 1, x2 == 3 before scaling
        assert y2 / y1 == pytest.approx(2.0)  # y1 == 2, y2 == 4 before scaling
        assert element.type == "test_class"
