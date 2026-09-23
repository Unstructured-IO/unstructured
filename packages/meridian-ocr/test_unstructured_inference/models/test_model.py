import json
import threading
import time
from typing import Any
from unittest import mock

import numpy as np
import pytest

import unstructured_inference.models.base as models
from unstructured_inference.inference.layoutelement import LayoutElement, LayoutElements
from unstructured_inference.models.unstructuredmodel import (
    ModelNotInitializedError,
    UnstructuredObjectDetectionModel,
)


class MockModel(UnstructuredObjectDetectionModel):
    call_count = 0

    def __init__(self):
        self.initializer = mock.MagicMock()
        super().__init__()

    def initialize(self, *args, **kwargs):
        return self.initializer(self, *args, **kwargs)

    def predict(self, x: Any) -> Any:
        return LayoutElements(element_coords=np.array([]))


MOCK_MODEL_TYPES = {
    "foo": {
        "input_shape": (640, 640),
    },
}


def test_get_model(monkeypatch):
    monkeypatch.setattr(models, "models", {})
    with mock.patch.dict(models.model_class_map, {"yolox": MockModel}):
        assert isinstance(models.get_model("yolox"), MockModel)


def test_get_model_threaded(monkeypatch):
    """Test that get_model works correctly when called from multiple threads simultaneously."""
    monkeypatch.setattr(models, "models", {})

    # Results and exceptions from threads will be stored here
    results = []
    exceptions = []

    def get_model_worker(thread_id):
        """Worker function for each thread."""
        try:
            model = models.get_model("yolox")
            results.append((thread_id, model))
        except Exception as e:
            exceptions.append((thread_id, e))

    # Create and start multiple threads
    num_threads = 10
    threads = []

    with mock.patch.dict(models.model_class_map, {"yolox": MockModel}):
        for i in range(num_threads):
            thread = threading.Thread(target=get_model_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    # Verify no exceptions occurred
    assert len(exceptions) == 0, f"Exceptions occurred in threads: {exceptions}"

    # Verify all threads got results
    assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"

    # Verify all results are MockModel instances
    for thread_id, model in results:
        assert isinstance(model, MockModel), (
            f"Thread {thread_id} got unexpected model type: {type(model)}"
        )


def test_get_model_concurrent_different_models(monkeypatch):
    """Test that different models can load in parallel without serialization."""
    monkeypatch.setattr(models, "models", {})

    # Track initialization timing
    init_events = []
    init_lock = threading.Lock()

    class SlowMockModel(MockModel):
        def __init__(self):
            super().__init__()
            self.model_name = None

        def initialize(self, *args, **kwargs):
            with init_lock:
                init_events.append((self.model_name, "start"))
            time.sleep(0.1)  # Simulate slow loading
            with init_lock:
                init_events.append((self.model_name, "end"))
            return super().initialize(*args, **kwargs)

    # Store model names in instances
    def create_model_with_name(name):
        def factory():
            model = SlowMockModel()
            model.model_name = name
            return model

        return factory

    results = []

    def worker(model_name):
        models.get_model(model_name)  # Load the model
        results.append(model_name)

    # Load 2 different models concurrently
    threads = []
    mock_config = {"input_shape": (640, 640)}
    with (
        mock.patch.dict(
            models.model_class_map,
            {
                "yolox": create_model_with_name("yolox"),
                "detectron2": create_model_with_name("detectron2"),
            },
        ),
        mock.patch.dict(models.model_config_map, {"yolox": mock_config, "detectron2": mock_config}),
    ):
        for model_name in ["yolox", "detectron2"]:
            thread = threading.Thread(target=worker, args=(model_name,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    # Both models should load successfully
    assert len(results) == 2

    # Verify parallel execution (both start before either ends)
    assert len(init_events) == 4, f"Expected 4 events (2 starts + 2 ends), got {len(init_events)}"

    # True parallelism means both models start before either finishes
    # Find when the first model finishes
    first_end_idx = next(
        (i for i, (_, event_type) in enumerate(init_events) if event_type == "end"), None
    )
    assert first_end_idx is not None, "No 'end' event found"

    # Count how many models started before the first one finished
    starts_before_first_end = sum(
        1 for _, event_type in init_events[:first_end_idx] if event_type == "start"
    )
    assert starts_before_first_end == 2, (
        f"Expected both models to start before either finishes (parallel execution), "
        f"but only {starts_before_first_end} started before first completion. "
        f"Events: {init_events}"
    )


def test_register_new_model():
    assert "foo" not in models.model_class_map
    assert "foo" not in models.model_config_map
    models.register_new_model(MOCK_MODEL_TYPES, MockModel)
    assert "foo" in models.model_class_map
    assert "foo" in models.model_config_map
    model = models.get_model("foo")
    assert len(model.initializer.mock_calls) == 1
    assert model.initializer.mock_calls[0][-1] == MOCK_MODEL_TYPES["foo"]
    assert isinstance(model, MockModel)
    # unregister the new model by reset to default
    models.model_class_map, models.model_config_map = models.get_default_model_mappings()
    assert "foo" not in models.model_class_map
    assert "foo" not in models.model_config_map


def test_get_model_with_lazydict_config(monkeypatch):
    """get_model must unpack a LazyDict config into initialize() without
    depending on Mapping.keys() — prevents regression of
    'argument after ** must be a mapping, not LazyDict' in prod.
    """
    from unstructured_inference.utils import LazyDict, LazyEvaluateInfo

    monkeypatch.setattr(models, "models", {})

    evaluated = []

    def _fake_download(path):
        evaluated.append(path)
        return path

    lazy_config = LazyDict(
        model_path=LazyEvaluateInfo(_fake_download, "/tmp/weights.onnx"),
        input_shape=(640, 640),
    )

    with (
        mock.patch.dict(models.model_class_map, {"lazy_mock": MockModel}),
        mock.patch.dict(models.model_config_map, {"lazy_mock": lazy_config}),
    ):
        model = models.get_model("lazy_mock")

    assert isinstance(model, MockModel)
    assert evaluated == ["/tmp/weights.onnx"]
    model.initializer.assert_called_once_with(
        model,
        model_path="/tmp/weights.onnx",
        input_shape=(640, 640),
    )


def test_raises_invalid_model():
    with pytest.raises(models.UnknownModelException):
        models.get_model("fake_model")


def test_raises_uninitialized():
    with pytest.raises(ModelNotInitializedError):
        models.UnstructuredDetectronONNXModel().predict(None)


def test_model_initializes_once():
    from unstructured_inference.inference import layout

    with (
        mock.patch.dict(models.model_class_map, {"yolox": MockModel}),
        mock.patch.object(
            models,
            "models",
            {},
        ),
    ):
        doc = layout.DocumentLayout.from_file("sample-docs/loremipsum.pdf")
        doc.pages[0].detection_model.initializer.assert_called_once()


def test_deduplicate_detected_elements():
    import numpy as np

    from unstructured_inference.inference.elements import intersections
    from unstructured_inference.inference.layout import DocumentLayout
    from unstructured_inference.models.base import get_model

    model = get_model("yolox_quantized")
    # model.confidence_threshold=0.5
    file = "sample-docs/example_table.jpg"
    doc = DocumentLayout.from_image_file(
        file,
        model,
    )
    known_elements = [e.bbox for e in doc.pages[0].elements if e.type != "UncategorizedText"]
    # Compute intersection matrix
    intersections_mtx = intersections(*known_elements)
    # Get rid off diagonal (cause an element will always intersect itself)
    np.fill_diagonal(intersections_mtx, False)
    # Now all the elements should be False, because any intersection remains
    assert not intersections_mtx.any()


def test_enhance_regions():
    from unstructured_inference.inference.elements import Rectangle
    from unstructured_inference.models.base import get_model

    elements = [
        LayoutElement(bbox=Rectangle(0, 0, 1, 1)),
        LayoutElement(bbox=Rectangle(0.01, 0.01, 1.01, 1.01)),
        LayoutElement(bbox=Rectangle(0.02, 0.02, 1.02, 1.02)),
        LayoutElement(bbox=Rectangle(0.03, 0.03, 1.03, 1.03)),
        LayoutElement(bbox=Rectangle(0.04, 0.04, 1.04, 1.04)),
        LayoutElement(bbox=Rectangle(0.05, 0.05, 1.05, 1.05)),
        LayoutElement(bbox=Rectangle(0.06, 0.06, 1.06, 1.06)),
        LayoutElement(bbox=Rectangle(0.07, 0.07, 1.07, 1.07)),
        LayoutElement(bbox=Rectangle(0.08, 0.08, 1.08, 1.08)),
        LayoutElement(bbox=Rectangle(0.09, 0.09, 1.09, 1.09)),
        LayoutElement(bbox=Rectangle(0.10, 0.10, 1.10, 1.10)),
    ]
    model = get_model("yolox_tiny")
    elements = model.enhance_regions(elements, 0.5)
    assert len(elements) == 1
    assert (
        elements[0].bbox.x1,
        elements[0].bbox.y1,
        elements[0].bbox.x2,
        elements[0].bbox.x2,
    ) == (
        0,
        0,
        1.10,
        1.10,
    )


def test_clean_type():
    from unstructured_inference.inference.layout import LayoutElement
    from unstructured_inference.models.base import get_model

    elements = [
        LayoutElement.from_coords(
            0.6,
            0.6,
            0.65,
            0.65,
            type="Table",
        ),  # One little table nested inside all the others
        LayoutElement.from_coords(0.5, 0.5, 0.7, 0.7, type="Table"),  # One nested table
        LayoutElement.from_coords(0, 0, 1, 1, type="Table"),  # Big table
        LayoutElement.from_coords(0.01, 0.01, 1.01, 1.01),
        LayoutElement.from_coords(0.02, 0.02, 1.02, 1.02),
        LayoutElement.from_coords(0.03, 0.03, 1.03, 1.03),
        LayoutElement.from_coords(0.04, 0.04, 1.04, 1.04),
        LayoutElement.from_coords(0.05, 0.05, 1.05, 1.05),
    ]
    model = get_model("yolox_tiny")
    elements = model.clean_type(elements, type_to_clean="Table")
    assert len(elements) == 1
    assert (
        elements[0].bbox.x1,
        elements[0].bbox.y1,
        elements[0].bbox.x2,
        elements[0].bbox.x2,
    ) == (0, 0, 1, 1)


def test_env_variables_override_default_model(monkeypatch):
    # When an environment variable specifies a different default model and we call get_model with no
    # args, we should get back the model the env var calls for
    monkeypatch.setattr(models, "models", {})
    with (
        mock.patch.dict(
            models.os.environ,
            {"UNSTRUCTURED_DEFAULT_MODEL_NAME": "yolox"},
        ),
        mock.patch.dict(models.model_class_map, {"yolox": MockModel}),
    ):
        model = models.get_model()
    assert isinstance(model, MockModel)


def test_env_variables_override_initialization_params(monkeypatch):
    # When initialization params are specified in an environment variable, and we call get_model, we
    # should see that the model was initialized with those params
    monkeypatch.setattr(models, "models", {})
    fake_label_map = {"1": "label1", "2": "label2"}
    with (
        mock.patch.dict(
            models.os.environ,
            {"UNSTRUCTURED_DEFAULT_MODEL_INITIALIZE_PARAMS_JSON_PATH": "fake_json.json"},
        ),
        mock.patch.object(models, "DEFAULT_MODEL", "fake"),
        mock.patch.dict(
            models.model_class_map,
            {"fake": mock.MagicMock()},
        ),
        mock.patch(
            "builtins.open",
            mock.mock_open(
                read_data='{"model_path": "fakepath", "label_map": '
                + json.dumps(fake_label_map)
                + "}",
            ),
        ),
    ):
        model = models.get_model()
    model.initialize.assert_called_once_with(
        model_path="fakepath",
        label_map={1: "label1", 2: "label2"},
    )
