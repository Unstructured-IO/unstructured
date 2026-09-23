<h3 align="center">
  <img
    src="https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/img/unstructured_logo.png"
    height="200"
  >

</h3>

<h3 align="center">
  <p>Open-Source Pre-Processing Tools for Unstructured Data</p>
</h3>

The `unstructured-inference` repo contains hosted model inference code for layout parsing models. 
These models are invoked via API as part of the partitioning bricks in the `unstructured` package.

**Requires Python >=3.11, <3.14.**

## Installation

### Package

```shell
pip install unstructured-inference
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

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```shell
# Clone and install all dependencies (including dev/test/lint groups)
git clone https://github.com/Unstructured-IO/unstructured-inference.git
cd unstructured-inference
make install
```

Run `make help` for a full list of available targets.

## Getting Started

To get started with the layout parsing model, use the following commands:

```python
from unstructured_inference.inference.layout import DocumentLayout

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
from unstructured_inference.models.base import get_model
from unstructured_inference.inference.layout import DocumentLayout

model = get_model("yolox")
layout = DocumentLayout.from_file("sample-docs/layout-parser-paper.pdf", detection_model=model)
```

### Using your own model

Any detection model can be used for in the `unstructured_inference` pipeline by wrapping the model in the `UnstructuredObjectDetectionModel` class. To integrate with the `DocumentLayout` class, a subclass of `UnstructuredObjectDetectionModel` must have a `predict` method that accepts a `PIL.Image.Image` and returns a list of `LayoutElement`s, and an `initialize` method, which loads the model and prepares it for inference.

## Security Policy

See our [security policy](https://github.com/Unstructured-IO/unstructured-inference/security/policy) for
information on how to report security vulnerabilities.

## Learn more

| Section | Description |
|-|-|
| [Unstructured Community Github](https://github.com/Unstructured-IO/community) | Information about Unstructured.io community projects  |
| [Unstructured Github](https://github.com/Unstructured-IO) | Unstructured.io open source repositories |
| [Company Website](https://unstructured.io) | Unstructured.io product and company info |
