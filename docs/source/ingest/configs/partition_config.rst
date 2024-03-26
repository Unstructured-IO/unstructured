Partition Configuration
=========================

A standard partition configuration is a collection of parameters designed to oversee document partitioning,
whether executed through API integration or by the unstructured library on a local system. These parameters serve a
dual role, encompassing those passed to the partition method for the initial segmentation of documents and those
responsible for coordinating data after processing, including the dynamic metadata associated with each element.

Configs for Partitioning
-------------------------

* ``pdf_infer_table_structure``: Deprecated! Use skip_infer_table_types to opt out of table extraction for any file type. If False and strategy=hi_res, no Table Elements will be extracted from pdf files regardless of skip_infer_table_types contents.
* ``skip_infer_table_types``: List of document types that you want to skip table extraction with.
* ``strategy (default auto)``: The strategy to use for partitioning PDF/image. Uses a layout detection model if set to 'hi_res', otherwise partition simply extracts the text from the document and processes it.
* ``ocr_languages``: The languages present in the document, for use in partitioning and/or OCR. For partitioning image or pdf documents with Tesseract, you'll first need to install the appropriate Tesseract language pack if running via local unstructured library. For other partitions, language is detected using naive Bayesian filter via `langdetect`. Multiple languages indicates text could be in either language.
* ``encoding``: The encoding method used to decode the text input. If None, utf-8 will be used.

Configs for the Process
-------------------------

* ``fields_include (default ["element_id", "text", "type", "metadata", "embeddings"])``: Fields to include in the output JSON.
* ``flatten_metadata (default False)``: If set to true, the hierarchical metadata structure is flattened to have all values exist at the top level.
* ``metadata_exclude``: Values from the metadata to exclude from the output
* ``metadata_include``: If provided, only these values will be preserved in the metadata output.
* ``partition_endpoint (default https://api.unstructured.io/general/v0/general)``: If using the api, will send requests to this endpoint.
* ``partition_by_api (default False)``: If set to True, will use the api to run partitioning.
* ``api_key``: api key needed to access the Unstructured api.
