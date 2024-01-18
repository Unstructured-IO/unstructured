.. role:: raw-html(raw)
    :format: html

Models
======

Depending on your need, ``Unstructured`` provides OCR-based and Transformer-based models to detect elements in the documents. The models are useful to detect the complex layout in the documents and predict the element types.

**Basic usage:**

.. code:: python

    elements = partition(filename=filename,
                         strategy="hi_res",
                         hi_res_model_name="yolox")

.. note::
    * To use any model with the partition, set the ``strategy`` to ``hi_res`` as shown above.
    * To maintain the consistency between the ``unstructured`` and ``unstructured-api`` libraries, we are deprecating the ``model_name`` parameter. Please use ``hi_res_model_name`` parameter when specifing a model.

:raw-html:`<br />`
**List of Available Models in the Partitions:**

* ``detectron2_onnx`` is a Computer Vision model by Facebook AI that provides object detection and segmentation algorithms with ONNX Runtime. It is the fastest model with the ``hi_res`` strategy.
* ``yolox`` is a single-stage real-time object detector that modifies YOLOv3 with a DarkNet53 backbone.
* ``yolox_quantized``: runs faster than YoloX and its speed is closer to Detectron2.
* ``chipper`` (beta version): the Chipper model is Unstructured’s in-house image-to-text model based on transformer-based Visual Document Understanding (VDU) models.


Using a Non-Default Model
^^^^^^^^^^^^^^^^^^^^^^^^^

``Unstructured`` will download the model specified in ``UNSTRUCTURED_HI_RES_MODEL_NAME`` environment variable. If not defined, it will download the default model.

There are three ways you can use the non-default model as follows:

1. Store the model name in the environment variable

.. code:: python

    import os
    from unstructured.partition.pdf import partition_pdf

    os.environ["UNSTRUCTURED_HI_RES_MODEL_NAME"] = "yolox"

    out_yolox = partition_pdf("example-docs/layout-parser-paper-fast.pdf", strategy="hi_res")


2. Pass the model name in the ``partition`` function.

.. code:: python

    filename = "example-docs/layout-parser-paper-fast.pdf"

    elements = partition(filename=filename,
                         strategy="hi_res",
                         hi_res_model_name="yolox")

3. Use `unstructured-inference <url_>`_ library.

.. _url: https://github.com/Unstructured-IO/unstructured-inference

.. code:: python

    from unstructured_inference.models.base import get_model
    from unstructured_inference.inference.layout import DocumentLayout

    model = get_model("yolox")
    layout = DocumentLayout.from_file("sample-docs/layout-parser-paper.pdf", detection_model=model)


Bring Your Own Models
^^^^^^^^^^^^^^^^^^^^^

**Utilizing Layout Detection Model Zoo**

In the `LayoutParser <layout_>`_ library, you can use various pre-trained models available in the `model zoo <modelzoo_>`_ for document layout analysis. Here's a guide on leveraging this feature using the ``UnstructuredDetectronModel`` class in ``unstructured-inference`` library.

The ``UnstructuredDetectronModel`` class in ``unstructured_inference.models.detectron2`` uses the ``faster_rcnn_R_50_FPN_3x`` model pretrained on ``DocLayNet``. But any model in the model zoo can be used by using different construction parameters. ``UnstructuredDetectronModel`` is a light wrapper around the LayoutParser's ``Detectron2LayoutModel`` object, and accepts the same arguments.

.. _modelzoo: https://layout-parser.readthedocs.io/en/latest/notes/modelzoo.html

.. _layout: https://layout-parser.readthedocs.io/en/latest/api_doc/models.html#layoutparser.models.Detectron2LayoutModel

**Using Your Own Object Detection Model**

To seamlessly integrate your custom detection and extraction models into ``unstructured_inference`` pipeline, start by wrapping your model within the ``UnstructuredObjectDetectionModel`` class. This class acts as an intermediary between your detection model and Unstructured workflow.

Ensure your ``UnstructuredObjectDetectionModel`` subclass incorporates two vital methods:

1. The ``predict`` method, which should be designed to accept a ``PIL.Image.Image`` type and return a list of ``LayoutElements``, facilitating the communication of your model's results.
2. The ``initialize`` method is essential for loading and prepping your model for inference, guaranteeing its readiness for any incoming tasks.

It's important that your model's outputs, specifically from the predict method, integrate smoothly with the DocumentLayout class for optimal performance.

