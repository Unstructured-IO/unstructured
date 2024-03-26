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

extract_image_block_types
-------------------------
- **Type**: array
- **Description**: The types of image blocks to extract from the document. Supports various Element types.
- **Example**: ['Image', 'Table']

hi_res_model_name
-----------------
- **Type**: string
- **Description**: The name of the inference model used when strategy is hi_res.
- **Example**: yolox

include_page_breaks
-------------------
- **Type**: boolean
- **Description**: When true, the output will include page break elements when the filetype supports
  it. Default: false.

languages
---------
- **Type**: array
- **Description**: The languages present in the document, for use in partitioning and/or OCR.
- **Default**: []
- **Example**: [eng]

pdf_infer_table_structure
-------------------------
- **Type**: boolean
- **Description**: Deprecated! Use skip_infer_table_types to opt out of table extraction for any file type. If False and strategy=hi_res, no Table Elements will be extracted from pdf files regardless of skip_infer_table_types contents.

skip_infer_table_types
----------------------
- **Type**: array
- **Description**: The document types that you want to skip table extraction with. Default: ['pdf', 'jpg', 'png', 'heic'].

xml_keep_tags
-------------
- **Type**: boolean
- **Description**: If True, will retain the XML tags in the output. Otherwise it will simply extract the text from within the tags. Only applies to partition_xml.


Chunking Parameters
-------------------

The following parameters control chunking behavior. Chunking is automatically performed after
partitioning when a value is provided for the ``chunking_strategy`` argument. The remaining chunking
parameters are only operative when a chunking strategy is specified. Note that not all chunking
parameters apply to all chunking strategies. Any chunking arguments not supported by the selected
chunker are ignored.

chunking_strategy
-----------------
- **Type**: string
- **Description**: Use one of the supported strategies to chunk the returned elements. When omitted,
  no chunking is performed and any other chunking parameters provided are ignored.
- **Valid values**: ``"basic"``, ``"by_title"``

combine_under_n_chars
---------------------
- **Type**: integer
- **Applicable Chunkers**: "by_title" only
- **Description**: When chunking strategy is set to "by_title", combine small chunks until the
  combined chunk reaches a length of n chars. This can mitigate the appearance of small chunks
  created by short paragraphs, not intended as section headings, being identified as ``Title``
  elements in certain documents.
- **Default**: the same value as ``max_characters``
- **Example**: 500

include_orig_elements
---------------------
- **Type**: boolean
- **Applicable Chunkers**: All
- **Description**: Add the elements used to form each chunk to ``.metadata.orig_elements`` for that
  chunk. These can be used to recover the original text and metadata for individual elements when
  that is required, for example to identify the page-numbers or coordinates spanned by a chunk.
  When an element larger than ``max_characters`` is divided into two or more chunks via
  text-splitting, each of those chunks will contain the entire original chunk as the only item in
  its ``.metadata.orig_elements`` list.
- **Default**: true

max_characters
--------------
- **Type**: integer
- **Applicable Chunkers**: All
- **Description**: When chunking strategy is set, cut off new chunks after reaching a length of n
  chars (hard max).
- **Default**: 500

multipage_sections
------------------
- **Type**: boolean
- **Applicable Chunkers**: "by_title" only
- **Description**: When true and chunking strategy is set to "by_title", allows a chunk to include
  elements from more than one page. Otherwise chunks are broken on page boundaries.
- **Default**: true

new_after_n_chars
-----------------
- **Type**: integer
- **Applicable Chunkers**: "basic", "by_title"
- **Description**: When chunking strategy is set, cut off new chunk after reaching a length of n
  chars (soft max).
- **Default**: 1500
