Strategies
==========

The Unstructured library offers a variety of different ways to preprocess documents which can be specified by the “strategy” parameter.

**Basic usage:**

.. code:: python

    elements = partition(filename=filename, strategy='hi_res')

**Available options:**

* ``auto`` (default strategy): The "auto" strategy will choose the partitioning strategy based on document characteristics and the function kwargs.
* ``fast``: The “fast” strategy will leverage traditional NLP extraction techniques to quickly pull all the text elements. "Fast" strategy is not good for image based file types.
* ``hi_res``: The "hi_res" strategy will identify the layout of the document using ``detectron2``. The advantage of “hi_res” is that it uses the document layout to gain additional information about document elements. We recommend using this strategy if your use case is highly sensitive to correct classifications for document elements.
* ``ocr_only``: Leverage Optical Character Recognition to extract text from the image based files.

**These strategies are available on the following partition functions:**

+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Document Type                             | Partition Function             | Strategies                             | Table Support  | Options                                                                                                          |
+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| Images (`.png`/`.jpg`/`.heic`)            | `partition_image`              | "auto", "hi_res", "ocr_only"           | Yes            | Encoding; Include Page Breaks; Infer Table Structure; OCR Languages, Strategy                                    |
+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+
| PDFs (`.pdf`)                             | `partition_pdf`                | "auto", "fast", "hi_res", "ocr_only"   | Yes            | Encoding; Include Page Breaks; Infer Table Structure; Max Partition; OCR Languages, Strategy                     |
+-------------------------------------------+--------------------------------+----------------------------------------+----------------+------------------------------------------------------------------------------------------------------------------+