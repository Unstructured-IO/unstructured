API Parameters
==============

The endpoint of the API provides several parameters to customize the processing of documents. Below are the details of these parameters:

files
-----
- **Type**: string (binary format)
- **Description**: The file to extract.
- **Required**: true
- **Example**: File to be partitioned. `Example File <https://github.com/Unstructured-IO/unstructured/blob/98d3541909f64290b5efb65a226fc3ee8a7cc5ee/example-docs/layout-parser-paper.pdf>`_

strategy
--------
- **Type**: string
- **Description**: The strategy to use for partitioning PDF/image. Options are fast, hi_res, auto. Default: auto.
- **Example**: hi_res

gz_uncompressed_content_type
-----------------------------
- **Type**: string
- **Description**: If file is gzipped, use this content type after unzipping.
- **Example**: application/pdf

output_format
-------------
- **Type**: string
- **Description**: The format of the response. Supported formats are application/json and text/csv. Default: application/json.
- **Example**: application/json

coordinates
-----------
- **Type**: boolean
- **Description**: If true, return coordinates for each element. Default: false.

encoding
--------
- **Type**: string
- **Description**: The encoding method used to decode the text input. Default: utf-8.
- **Example**: utf-8

hi_res_model_name
-----------------
- **Type**: string
- **Description**: The name of the inference model used when strategy is hi_res.
- **Example**: yolox

include_page_breaks
-------------------
- **Type**: boolean
- **Description**: If True, the output will include page breaks if the filetype supports it. Default: false.

languages
---------
- **Type**: array
- **Description**: The languages present in the document, for use in partitioning and/or OCR.
- **Default**: []
- **Example**: [eng]

pdf_infer_table_structure
-------------------------
- **Type**: boolean
- **Description**: If True and strategy=hi_res, any Table Elements extracted from a PDF will include an additional metadata field, 'text_as_html'.

skip_infer_table_types
----------------------
- **Type**: array
- **Description**: The document types that you want to skip table extraction with. Default: ['pdf', 'jpg', 'png', 'heic'].

xml_keep_tags
-------------
- **Type**: boolean
- **Description**: If True, will retain the XML tags in the output. Otherwise it will simply extract the text from within the tags. Only applies to partition_xml.

chunking_strategy
-----------------
- **Type**: string
- **Description**: Use one of the supported strategies to chunk the returned elements. Currently supports: by_title.
- **Example**: by_title

multipage_sections
------------------
- **Type**: boolean
- **Description**: If chunking strategy is set, determines if sections can span multiple sections. Default: true.

combine_under_n_chars
---------------------
- **Type**: integer
- **Description**: If chunking strategy is set, combine elements until a section reaches a length of n chars. Default: 500.
- **Example**: 500

new_after_n_chars
-----------------
- **Type**: integer
- **Description**: If chunking strategy is set, cut off new sections after reaching a length of n chars (soft max). Default: 1500.
- **Example**: 1500

max_characters
--------------
- **Type**: integer
- **Description**: If chunking strategy is set, cut off new sections after reaching a length of n chars (hard max). Default: 1500.
- **Example**: 1500

extract_image_block_types
-------------------------
- **Type**: array
- **Description**: The types of image blocks to extract from the document. Supports various Element types.
- **Example**: ['Image', 'Table']

extract_image_block_to_payload
------------------------------
- **Type**: boolean
- **Description**: This parameter facilitates the inclusion of element data directly within the payload, especially for web-based applications or APIs.
- **Example**: true