.. role:: raw-html(raw)
    :format: html

Models
======

Depending on your need, ``Unstructured`` provides OCR-based and Transformer-based models to detect elements in the documents. The models are useful to detect the complex layout in the documents and predict the element types.

**Basic usage:**

.. code:: python

    elements = partition(filename=filename, strategy='hi_res', model_name='detectron2_onnx')

Notes:

* To use a the detection model, set: ``strategy='hi_res'``.
* When ``model_name`` is not defined, the inferences will fall back to the default model.

:raw-html:`<br />`
**Tables Extraction**

You can leverage the models to extract **tables** from the following file types by setting ``infer_table_structure=True`` and ``strategy='hi_res'``.

+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Document Type                             | Partition Function             | Strategies                             | Table Support  | Options                                                                                                          |
+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Images (`.png`/`.jpg`)                    | `partition_image`              | "auto", "hi_res", "ocr_only"           | Yes            | Encoding; Include Page Breaks; Infer Table Structure; OCR Languages, Strategy                                    |
+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| PDFs (`.pdf`)                             | `partition_pdf`                | "auto", "fast", "hi_res", "ocr_only"   | Yes            | Encoding; Include Page Breaks; Infer Table Structure; Max Partition; OCR Languages, Strategy                     |
+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
:raw-html:`<br />`
**List of Available Models:**

* ``detectron2_onnx`` (*default model*): The Detectron2 model is part of Facebook AI Research’s next generation library. It is the fastest ``hi_res`` strategy.
* ``yolox``: The YoloX model tends to outperform the Detectron2 model in table extraction.
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
    elements = partition(filename=filename, strategy='hi_res', model_name='yolox')

3. Use `"unstructured-inference" <url_>`_ library.

.. _url: https://github.com/Unstructured-IO/unstructured-inference

.. code:: python

    from unstructured_inference.models.base import get_model
    from unstructured_inference.inference.layout import DocumentLayout

    model = get_model("yolox")
    layout = DocumentLayout.from_file("sample-docs/layout-parser-paper.pdf", detection_model=model)



Bring Your Own Model
^^^^^^^^^^^^^^^^^^^^



