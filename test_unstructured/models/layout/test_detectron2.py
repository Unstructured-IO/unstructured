import pytest
from unittest.mock import patch

import unstructured.models.layout.detectron2 as detectron2


class MockDetectron2LayoutModel:
    def __init__(self, *args, **kwargs):
        pass


def test_load_model(monkeypatch):
    monkeypatch.setattr(detectron2, "Detectron2LayoutModel", MockDetectron2LayoutModel)

    with patch.object(detectron2, "is_detectron2_available", return_value=True):
        detectron2.load_model()

    assert isinstance(detectron2.model, MockDetectron2LayoutModel)


def test_load_model_raises_when_not_available():
    with patch.object(detectron2, "is_detectron2_available", return_value=False):
        with pytest.raises(ImportError):
            detectron2.load_model()
