# meridian_ocr

Model inference for document layout parsing: layout detection (YOLOX, Detectron2 ONNX), table structure
recognition (Table Transformer), PDF rendering, and the layout element types consumed by
[`meridian_partition`](../meridian-partition) for its `hi_res` strategy.

**Requires Python >=3.11, <3.14.**

Ported from [`unstructured-inference`](https://github.com/Unstructured-IO/unstructured-inference) 1.6.13
(commit `fc64017`, Apache-2.0) and renamed to `meridian_ocr`.

Model weights are downloaded from private mirrors in the `Anacreonresearch` Hugging Face organization, pinned
to fixed revisions (`YOLOX_REPO`/`YOLOX_REVISION` in `models/yolox.py`, the detectron2 constants in
`models/detectron2onnx.py`, `DEFAULT_MODEL`/`DEFAULT_MODEL_REVISION` in `models/tables.py`). Set `HF_TOKEN`
to a token with read access to that organization.

## Installation

### Package

```shell
pip install meridian_ocr
```

### Detectron2

[Detectron2](https://github.com/facebookresearch/detectron2) is required for using models from the [layoutparser model zoo](#using-models-from-the-layoutparser-model-zoo) 
but is not automatically installed with this package. 
For MacOS and Linux, build from source with:
```shell
pip install 'git+https://github.com/facebookresearch/detectron2.git@57bdb21249d5418c130d54e2ebdc94dda7a4c01a'
```
Other install options can be found in the 
[Detectron2 installation guide](https://detectron2.readthedocs.io/en/latest/tutorials/install.html).

Windows is not officially supported by Detectron2, but some users are able to install it anyway. 
See discussion [here](https://layout-parser.github.io/tutorials/installation#for-windows-users) for 
tips on installing Detectron2 on Windows.

### Development Setup

This package is part of a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/); the lockfile
and virtual environment live at the repository root. From `packages/meridian-ocr`:

```shell
# Install the package with all dependency groups (dev/test/lint)
make install
```

Run `make help` for a full list of available targets. Tests resolve `sample-docs/` relative to the package
directory, so run them from here (`make test`).

## Getting Started

To get started with the layout parsing model, use the following commands:

```python
from meridian_ocr.inference.layout import DocumentLayout

layout = DocumentLayout.from_file("sample-docs/loremipsum.pdf")

print(layout.pages[0].elements)
```

Once the model has detected the layout and OCR'd the document, the text extracted from the first 
page of the sample document will be displayed.
You can convert a given element to a `dict` by running the `.to_dict()` method.

## Models

The inference pipeline operates by finding text elements in a document page using a detection model, then extracting the contents of the elements using direct extraction (if available), OCR, and optionally table inference models.

We offer several detection models including [Detectron2](https://github.com/facebookresearch/detectron2) and [YOLOX](https://github.com/Megvii-BaseDetection/YOLOX).

### Using a non-default model

When doing inference, an alternate model can be used by passing the model object to the ingestion method via the `model` parameter. The `get_model` function can be used to construct one of our out-of-the-box models from a keyword, e.g.:
```python
from meridian_ocr.models.base import get_model
from meridian_ocr.inference.layout import DocumentLayout

model = get_model("yolox")
layout = DocumentLayout.from_file("sample-docs/layout-parser-paper.pdf", detection_model=model)
```

### Using your own model

Any detection model can be used for in the `meridian_ocr` pipeline by wrapping the model in the `MeridianOCRObjectDetectionModel` class. To integrate with the `DocumentLayout` class, a subclass of `MeridianOCRObjectDetectionModel` must have a `predict` method that accepts a `PIL.Image.Image` and returns a list of `LayoutElement`s, and an `initialize` method, which loads the model and prepares it for inference.

The default model can also be selected with the `MERIDIAN_OCR_DEFAULT_MODEL_NAME` environment variable, and
its initialization parameters loaded from the JSON file named by
`MERIDIAN_OCR_DEFAULT_MODEL_INITIALIZE_PARAMS_JSON_PATH`.

## Security Policy

See the upstream [security policy](https://github.com/Unstructured-IO/unstructured-inference/security/policy) for
information on how to report security vulnerabilities.
