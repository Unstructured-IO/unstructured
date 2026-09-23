from __future__ import annotations

import json
import os
import threading
from typing import Dict, Optional, Tuple, Type

from unstructured_inference.models.detectron2onnx import (
    MODEL_TYPES as DETECTRON2_ONNX_MODEL_TYPES,
)
from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel
from unstructured_inference.models.unstructuredmodel import UnstructuredModel
from unstructured_inference.models.yolox import MODEL_TYPES as YOLOX_MODEL_TYPES
from unstructured_inference.models.yolox import UnstructuredYoloXModel
from unstructured_inference.utils import LazyDict

DEFAULT_MODEL = "yolox"


class Models(object):
    """Singleton container for loaded models.

    Thread Safety:
    - Singleton initialization protected by _lock (double-check pattern)
    - Dict operations (__contains__, __getitem__, __setitem__) rely on CPython's GIL
      for atomicity. Individual dict operations are atomic in CPython.
    - Per-model locks in get_model() prevent concurrent initialization of same model
    - This implementation is CPython-specific and may need changes for Python 3.13+
      free-threaded mode or alternative Python implementations without GIL
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """return an instance if one already exists otherwise create an instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Models, cls).__new__(cls)
                    cls.models: Dict[str, UnstructuredModel] = {}
        return cls._instance

    def __contains__(self, key):
        """Check if model exists. Atomic operation under CPython GIL."""
        return key in self.models

    def __getitem__(self, key: str):
        """Get model by name. Atomic operation under CPython GIL."""
        return self.models.__getitem__(key)

    def __setitem__(self, key: str, value: UnstructuredModel):
        """Store model. Atomic operation under CPython GIL."""
        self.models[key] = value


models: Models = Models()

# Per-model locks for parallel loading of different models
# Current implementation: Unbounded dictionary grows with unique model names
# Memory impact: ~200 bytes per lock. Acceptable for <100 models (~20KB).
# For >1000 models: Consider lock striping (fixed 128 locks, ~25KB, 0.8% collision rate)
# Note: WeakValueDictionary is NOT suitable - locks would be GC'd immediately
_models_locks: Dict[str, threading.Lock] = {}
_models_locks_lock = threading.Lock()


def get_default_model_mappings() -> Tuple[
    Dict[str, Type[UnstructuredModel]],
    Dict[str, dict | LazyDict],
]:
    """default model mappings for models that are in `unstructured_inference` repo"""
    return {
        **dict.fromkeys(DETECTRON2_ONNX_MODEL_TYPES, UnstructuredDetectronONNXModel),
        **dict.fromkeys(YOLOX_MODEL_TYPES, UnstructuredYoloXModel),
    }, {**DETECTRON2_ONNX_MODEL_TYPES, **YOLOX_MODEL_TYPES}


model_class_map, model_config_map = get_default_model_mappings()


def register_new_model(model_config: dict, model_class: UnstructuredModel):
    """Register this model in model_config_map and model_class_map.

    Those maps are updated with the with the new model class information.
    """
    model_config_map.update(model_config)
    model_class_map.update(dict.fromkeys(model_config, model_class))


def get_model(model_name: Optional[str] = None) -> UnstructuredModel:
    """Gets the model object by model name.

    Thread-safe with per-model locks to allow parallel loading of different models
    while preventing duplicate initialization of the same model.

    Thread-safety maintained:
    - _models_locks_lock protects lock dictionary operations
    - Per-model locks protect model initialization
    - Double-check pattern prevents duplicate loads
    """
    if model_name is None:
        default_name_from_env = os.environ.get("UNSTRUCTURED_DEFAULT_MODEL_NAME")
        model_name = default_name_from_env if default_name_from_env is not None else DEFAULT_MODEL

    # Fast path: model already loaded
    if model_name in models:
        return models[model_name]

    # Get or create lock for this specific model
    with _models_locks_lock:
        if model_name not in _models_locks:
            _models_locks[model_name] = threading.Lock()

    model_lock = _models_locks[model_name]

    # Double-check pattern with per-model lock
    with model_lock:
        if model_name in models:
            return models[model_name]

        initialize_param_json = os.environ.get(
            "UNSTRUCTURED_DEFAULT_MODEL_INITIALIZE_PARAMS_JSON_PATH"
        )
        if initialize_param_json is not None:
            with open(initialize_param_json) as fp:
                initialize_params = json.load(fp)
                label_map_int_keys = {
                    int(key): value for key, value in initialize_params["label_map"].items()
                }
                initialize_params["label_map"] = label_map_int_keys
        else:
            if model_name in model_config_map:
                initialize_params = model_config_map[model_name]
            else:
                raise UnknownModelException(f"Unknown model type: {model_name}")

        model: UnstructuredModel = model_class_map[model_name]()

        # Normalize to a plain dict via __iter__ + __getitem__. `**` unpacking
        # calls `.keys()` on the mapping, which LazyDict inherits from
        # collections.abc.Mapping — but we've seen environments where that
        # inherited method isn't found at call time, surfacing as
        # "argument after ** must be a mapping, not LazyDict".
        initialize_params = {k: initialize_params[k] for k in initialize_params}
        model.initialize(**initialize_params)
        models[model_name] = model
    return model


class UnknownModelException(Exception):
    """A model was requested with an unrecognized identifier."""

    pass
