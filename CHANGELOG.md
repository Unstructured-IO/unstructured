## 0.8.1

### Enhancements

* Add support for Python 3.11

### Features

### Fixes

* Fixed `auto` strategy detected scanned document as having extractable text and using `fast` strategy, resulting in no output.
* Fix list detection in MS Word documents.
* Don't instantiate an element with a coordinate system when there isn't a way to get its location data.

## 0.8.0

### Enhancements

* Allow model used for hi res pdf partition strategy to be chosen when called.
* Updated inference package

### Features

* Add `metadata_filename` parameter across all partition functions

### Fixes

* Update to ensure `convert_to_datafame` grabs all of the metadata fields.
* Adjust encoding recognition threshold value in `detect_file_encoding`
* Fix KeyError when `isd_to_elements` doesn't find a type
* Fix `_output_filename` for local connector, allowing single files to be written correctly to the disk

* Fix for cases where an invalid encoding is extracted from an email header.

### BREAKING CHANGES

* Information about an element's location is no longer returned as top-level attributes of an element. Instead, it is returned in the `coordinates` attribute of the element's metadata.

## 0.7.12

### Enhancements

* Adds `include_metadata` kwarg to `partition_doc`, `partition_docx`, `partition_email`, `partition_epub`, `partition_json`, `partition_msg`, `partition_odt`, `partition_org`, `partition_pdf`, `partition_ppt`, `partition_pptx`, `partition_rst`, and `partition_rtf`
### Features

* Add Elasticsearch connector for ingest cli to pull specific fields from all documents in an index.
* Adds Dropbox connector

### Fixes

* Fix tests that call unstructured-api by passing through an api-key
* Fixed page breaks being given (incorrect) page numbers
* Fix skipping download on ingest when a source document exists locally

## 0.7.11

### Enhancements

* More deterministic element ordering when using `hi_res` PDF parsing strategy (from unstructured-inference bump to 0.5.4)
* Make large model available (from unstructured-inference bump to 0.5.3)
* Combine inferred elements with extracted elements (from unstructured-inference bump to 0.5.2)
* `partition_email` and `partition_msg` will now process attachments if `process_attachments=True`
  and a attachment partitioning functions is passed through with `attachment_partitioner=partition`.

### Features

### Fixes

* Fix tests that call unstructured-api by passing through an api-key
* Fixed page breaks being given (incorrect) page numbers
* Fix skipping download on ingest when a source document exists locally

## 0.7.10

### Enhancements

* Adds a `max_partition` parameter to `partition_text`, `partition_pdf`, `partition_email`,
  `partition_msg` and `partition_xml` that sets a limit for the size of an individual
  document elements. Defaults to `1500` for everything except `partition_xml`, which has
  a default value of `None`.
* DRY connector refactor

### Features

* `hi_res` model for pdfs and images is selectable via environment variable.

### Fixes

* CSV check now ignores escaped commas.
* Fix for filetype exploration util when file content does not have a comma.
* Adds negative lookahead to bullet pattern to avoid detecting plain text line
  breaks like `-------` as list items.
* Fix pre tag parsing for `partition_html`
* Fix lookup error for annotated Arabic and Hebrew encodings

## 0.7.9

### Enhancements

* Improvements to string check for leafs in `partition_xml`.
* Adds --partition-ocr-languages to unstructured-ingest.

### Features

* Adds `partition_org` for processed Org Mode documents.

### Fixes

## 0.7.8

### Enhancements

### Features

* Adds Google Cloud Service connector

### Fixes

* Updates the `parse_email` for `partition_eml` so that `unstructured-api` passes the smoke tests
* `partition_email` now works if there is no message content
* Updates the `"fast"` strategy for `partition_pdf` so that it's able to recursively
* Adds recursive functionality to all fsspec connectors
* Adds generic --recursive ingest flag

## 0.7.7

### Enhancements

* Adds functionality to replace the `MIME` encodings for `eml` files with one of the common encodings if a `unicode` error occurs
* Adds missed file-like object handling in `detect_file_encoding`
* Adds functionality to extract charset info from `eml` files

### Features

* Added coordinate system class to track coordinate types and convert to different coordinate

### Fixes

* Adds an `html_assemble_articles` kwarg to `partition_html` to enable users to capture
  control whether content outside of `<article>` tags is captured when
  `<article>` tags are present.
* Check for the `xml` attribute on `element` before looking for pagebreaks in `partition_docx`.

## 0.7.6

### Enhancements

* Convert fast startegy to ocr_only for images
* Adds support for page numbers in `.docx` and `.doc` when user or renderer
  created page breaks are present.
* Adds retry logic for the unstructured-ingest Biomed connector

### Features

* Provides users with the ability to extract additional metadata via regex.
* Updates `partition_docx` to include headers and footers in the output.
* Create `partition_tsv` and associated tests. Make additional changes to `detect_filetype`.

### Fixes

* Remove fake api key in test `partition_via_api` since we now require valid/empty api keys
* Page number defaults to `None` instead of `1` when page number is not present in the metadata.
  A page number of `None` indicates that page numbers are not being tracked for the document
  or that page numbers do not apply to the element in question..
* Fixes an issue with some pptx files. Assume pptx shapes are found in top left position of slide
  in case the shape.top and shape.left attributes are `None`.

## 0.7.5

### Enhancements

* Adds functionality to sort elements in `partition_pdf` for `fast` strategy
* Adds ingest tests with `--fast` strategy on PDF documents
* Adds --api-key to unstructured-ingest

### Features

* Adds `partition_rst` for processed ReStructured Text documents.

### Fixes

* Adds handling for emails that do not have a datetime to extract.
* Adds pdf2image package as core requirement of unstructured (with no extras)

## 0.7.4

### Enhancements

* Allows passing kwargs to request data field for `partition_via_api` and `partition_multiple_via_api`
* Enable MIME type detection if libmagic is not available
* Adds handling for empty files in `detect_filetype` and `partition`.

### Features

### Fixes

* Reslove `grpcio` import issue on `weaviate.schema.validate_schema` for python 3.9 and 3.10
* Remove building `detectron2` from source in Dockerfile

## 0.7.3

### Enhancements

* Update IngestDoc abstractions and add data source metadata in ElementMetadata

### Features

### Fixes

* Pass `strategy` parameter down from `partition` for `partition_image`
* Filetype detection if a CSV has a `text/plain` MIME type
* `convert_office_doc` no longers prints file conversion info messages to stdout.
* `partition_via_api` reflects the actual filetype for the file processed in the API.

## 0.7.2

### Enhancements

* Adds an optional encoding kwarg to `elements_to_json` and `elements_from_json`
* Bump version of base image to use new stable version of tesseract

### Features

### Fixes

* Update the `read_txt_file` utility function to keep using `spooled_to_bytes_io_if_needed` for xml
* Add functionality to the `read_txt_file` utility function to handle file-like object from URL
* Remove the unused parameter `encoding` from `partition_pdf`
* Change auto.py to have a `None` default for encoding
* Add functionality to try other common encodings for html and xml files if an error related to the encoding is raised and the user has not specified an encoding.
* Adds benchmark test with test docs in example-docs
* Re-enable test_upload_label_studio_data_with_sdk
* File detection now detects code files as plain text
* Adds `tabulate` explicitly to dependencies
* Fixes an issue in `metadata.page_number` of pptx files
* Adds showing help if no parameters passed

## 0.7.1

### Enhancements

### Features

* Add `stage_for_weaviate` to stage `unstructured` outputs for upload to Weaviate, along with
  a helper function for defining a class to use in Weaviate schemas.
* Builds from Unstructured base image, built off of Rocky Linux 8.7, this resolves almost all CVE's in the image.

### Fixes

## 0.7.0

### Enhancements

* Installing `detectron2` from source is no longer required when using the `local-inference` extra.
* Updates `.pptx` parsing to include text in tables.

### Features

### Fixes

* Fixes an issue in `_add_element_metadata` that caused all elements to have `page_number=1`
  in the element metadata.
* Adds `.log` as a file extension for TXT files.
* Adds functionality to try other common encodings for email (`.eml`) files if an error related to the encoding is raised and the user has not specified an encoding.
* Allow passed encoding to be used in the `replace_mime_encodings`
* Fixes page metadata for `partition_html` when `include_metadata=False`
* A `ValueError` now raises if `file_filename` is not specified when you use `partition_via_api`
  with a file-like object.

## 0.6.11

### Enhancements

* Supports epub tests since pandoc is updated in base image

### Features


### Fixes


## 0.6.10

### Enhancements

* XLS support from auto partition

### Features

### Fixes

## 0.6.9

### Enhancements

* fast strategy for pdf now keeps element bounding box data
* setup.py refactor

### Features

### Fixes

* Adds functionality to try other common encodings if an error related to the encoding is raised and the user has not specified an encoding.
* Adds additional MIME types for CSV

## 0.6.8

### Enhancements

### Features

* Add `partition_csv` for CSV files.

### Fixes

## 0.6.7

### Enhancements

* Deprecate `--s3-url` in favor of `--remote-url` in CLI
* Refactor out non-connector-specific config variables
* Add `file_directory` to metadata
* Add `page_name` to metadata. Currently used for the sheet name in XLSX documents.
* Added a `--partition-strategy` parameter to unstructured-ingest so that users can specify
  partition strategy in CLI. For example, `--partition-strategy fast`.
* Added metadata for filetype.
* Add Discord connector to pull messages from a list of channels
* Refactor `unstructured/file-utils/filetype.py` to better utilise hashmap to return mime type.
* Add local declaration of DOCX_MIME_TYPES and XLSX_MIME_TYPES for `test_filetype.py`.

### Features

* Add `partition_xml` for XML files.
* Add `partition_xlsx` for Microsoft Excel documents.

### Fixes

* Supports `hml` filetype for partition as a variation of html filetype.
* Makes `pytesseract` a function level import in `partition_pdf` so you can use the `"fast"`
  or `"hi_res"` strategies if `pytesseract` is not installed. Also adds the
  `required_dependencies` decorator for the `"hi_res"` and `"ocr_only"` strategies.
* Fix to ensure `filename` is tracked in metadata for `docx` tables.

## 0.6.6

### Enhancements

* Adds an `"auto"` strategy that chooses the partitioning strategy based on document
  characteristics and function kwargs. This is the new default strategy for `partition_pdf`
  and `partition_image`. Users can maintain existing behavior by explicitly setting
  `strategy="hi_res"`.
* Added an additional trace logger for NLP debugging.
* Add `get_date` method to `ElementMetadata` for converting the datestring to a `datetime` object.
* Cleanup the `filename` attribute on `ElementMetadata` to remove the full filepath.

### Features

* Added table reading as html with URL parsing to `partition_docx` in docx
* Added metadata field for text_as_html for docx files

### Fixes

* `fileutils/file_type` check json and eml decode ignore error
* `partition_email` was updated to more flexibly handle deviations from the RFC-2822 standard.
  The time in the metadata returns `None` if the time does not match RFC-2822 at all.
* Include all metadata fields when converting to dataframe or CSV

## 0.6.5

### Enhancements

* Added support for SpooledTemporaryFile file argument.

### Features

### Fixes


## 0.6.4

### Enhancements

* Added an "ocr_only" strategy for `partition_pdf`. Refactored the strategy decision
  logic into its own module.

### Features

### Fixes

## 0.6.3

### Enhancements

* Add an "ocr_only" strategy for `partition_image`.

### Features

* Added `partition_multiple_via_api` for partitioning multiple documents in a single REST
  API call.
* Added `stage_for_baseplate` function to prepare outputs for ingestion into Baseplate.
* Added `partition_odt` for processing Open Office documents.

### Fixes

* Updates the grouping logic in the `partition_pdf` fast strategy to group together text
  in the same bounding box.

## 0.6.2

### Enhancements

* Added logic to `partition_pdf` for detecting copy protected PDFs and falling back
  to the hi res strategy when necessary.


### Features

* Add `partition_via_api` for partitioning documents through the hosted API.

### Fixes

* Fix how `exceeds_cap_ratio` handles empty (returns `True` instead of `False`)
* Updates `detect_filetype` to properly detect JSONs when the MIME type is `text/plain`.

## 0.6.1

### Enhancements

* Updated the table extraction parameter name to be more descriptive

### Features

### Fixes

## 0.6.0

### Enhancements

* Adds an `ssl_verify` kwarg to `partition` and `partition_html` to enable turning off
  SSL verification for HTTP requests. SSL verification is on by default.
* Allows users to pass in ocr language to `partition_pdf` and `partition_image` through
  the `ocr_language` kwarg. `ocr_language` corresponds to the code for the language pack
  in Tesseract. You will need to install the relevant Tesseract language pack to use a
  given language.

### Features

* Table extraction is now possible for pdfs from `partition` and `partition_pdf`.
* Adds support for extracting attachments from `.msg` files

### Fixes

* Adds an `ssl_verify` kwarg to `partition` and `partition_html` to enable turning off
  SSL verification for HTTP requests. SSL verification is on by default.

## 0.5.13

### Enhancements

* Allow headers to be passed into `partition` when `url` is used.

### Features

* `bytes_string_to_string` cleaning brick for bytes string output.

### Fixes

* Fixed typo in call to `exactly_one` in `partition_json`
* unstructured-documents encode xml string if document_tree is `None` in `_read_xml`.
* Update to `_read_xml` so that Markdown files with embedded HTML process correctly.
* Fallback to "fast" strategy only emits a warning if the user specifies the "hi_res" strategy.
* unstructured-partition-text_type exceeds_cap_ratio fix returns and how capitalization ratios are calculated
* `partition_pdf` and `partition_text` group broken paragraphs to avoid fragmented `NarrativeText` elements.
* .json files resolved as "application/json" on centos7 (or other installs with older libmagic libs)

## 0.5.12

### Enhancements

* Add OS mimetypes DB to docker image, mainly for unstructured-api compat.
* Use the image registry as a cache when building Docker images.
* Adds the ability for `partition_text` to group together broken paragraphs.
* Added method to utils to allow date time format validation

### Features
* Add Slack connector to pull messages for a specific channel

* Add --partition-by-api parameter to unstructured-ingest
* Added `partition_rtf` for processing rich text files.
* `partition` now accepts a `url` kwarg in addition to `file` and `filename`.

### Fixes

* Allow encoding to be passed into `replace_mime_encodings`.
* unstructured-ingest connector-specific dependencies are imported on demand.
* unstructured-ingest --flatten-metadata supported for local connector.
* unstructured-ingest fix runtime error when using --metadata-include.

## 0.5.11

### Enhancements

### Features

### Fixes

* Guard against null style attribute in docx document elements
* Update HTML encoding to better support foreign language characters

## 0.5.10

### Enhancements

* Updated inference package
* Add sender, recipient, date, and subject to element metadata for emails

### Features

* Added `--download-only` parameter to `unstructured-ingest`

### Fixes

* FileNotFound error when filename is provided but file is not on disk

## 0.5.9

### Enhancements

### Features

### Fixes

* Convert file to str in helper `split_by_paragraph` for `partition_text`

## 0.5.8

### Enhancements

* Update `elements_to_json` to return string when filename is not specified
* `elements_from_json` may take a string instead of a filename with the `text` kwarg
* `detect_filetype` now does a final fallback to file extension.
* Empty tags are now skipped during the depth check for HTML processing.

### Features

* Add local file system to `unstructured-ingest`
* Add `--max-docs` parameter to `unstructured-ingest`
* Added `partition_msg` for processing MSFT Outlook .msg files.

### Fixes

* `convert_file_to_text` now passes through the `source_format` and `target_format` kwargs.
  Previously they were hard coded.
* Partitioning functions that accept a `text` kwarg no longer raise an error if an empty
  string is passed (and empty list of elements is returned instead).
* `partition_json` no longer fails if the input is an empty list.
* Fixed bug in `chunk_by_attention_window` that caused the last word in segments to be cut-off
  in some cases.

### BREAKING CHANGES

* `stage_for_transformers` now returns a list of elements, making it consistent with other
  staging bricks

## 0.5.7

### Enhancements

* Refactored codebase using `exactly_one`
* Adds ability to pass headers when passing a url in partition_html()
* Added optional `content_type` and `file_filename` parameters to `partition()` to bypass file detection

### Features

* Add `--flatten-metadata` parameter to `unstructured-ingest`
* Add `--fields-include` parameter to `unstructured-ingest`

### Fixes

## 0.5.6

### Enhancements

* `contains_english_word()`, used heavily in text processing, is 10x faster.

### Features

* Add `--metadata-include` and `--metadata-exclude` parameters to `unstructured-ingest`
* Add `clean_non_ascii_chars` to remove non-ascii characters from unicode string

### Fixes

* Fix problem with PDF partition (duplicated test)

## 0.5.4

### Enhancements

* Added Biomedical literature connector for ingest cli.
* Add `FsspecConnector` to easily integrate any existing `fsspec` filesystem as a connector.
* Rename `s3_connector.py` to `s3.py` for readability and consistency with the
  rest of the connectors.
* Now `S3Connector` relies on `s3fs` instead of on `boto3`, and it inherits
  from `FsspecConnector`.
* Adds an `UNSTRUCTURED_LANGUAGE_CHECKS` environment variable to control whether or not language
  specific checks like vocabulary and POS tagging are applied. Set to `"true"` for higher
  resolution partitioning and `"false"` for faster processing.
* Improves `detect_filetype` warning to include filename when provided.
* Adds a "fast" strategy for partitioning PDFs with PDFMiner. Also falls back to the "fast"
  strategy if detectron2 is not available.
* Start deprecation life cycle for `unstructured-ingest --s3-url` option, to be deprecated in
  favor of `--remote-url`.

### Features

* Add `AzureBlobStorageConnector` based on its `fsspec` implementation inheriting
from `FsspecConnector`
* Add `partition_epub` for partitioning e-books in EPUB3 format.

### Fixes

* Fixes processing for text files with `message/rfc822` MIME type.
* Open xml files in read-only mode when reading contents to construct an XMLDocument.

## 0.5.3

### Enhancements

* `auto.partition()` can now load Unstructured ISD json documents.
* Simplify partitioning functions.
* Improve logging for ingest CLI.

### Features

* Add `--wikipedia-auto-suggest` argument to the ingest CLI to disable automatic redirection
  to pages with similar names.
* Add setup script for Amazon Linux 2
* Add optional `encoding` argument to the `partition_(text/email/html)` functions.
* Added Google Drive connector for ingest cli.
* Added Gitlab connector for ingest cli.

### Fixes

## 0.5.2

### Enhancements

* Fully move from printing to logging.
* `unstructured-ingest` now uses a default `--download_dir` of `$HOME/.cache/unstructured/ingest`
rather than a "tmp-ingest-" dir in the working directory.

### Features

### Fixes

* `setup_ubuntu.sh` no longer fails in some contexts by interpreting
`DEBIAN_FRONTEND=noninteractive` as a command
* `unstructured-ingest` no longer re-downloads files when --preserve-downloads
is used without --download-dir.
* Fixed an issue that was causing text to be skipped in some HTML documents.

## 0.5.1

### Enhancements

### Features

### Fixes

* Fixes an error causing JavaScript to appear in the output of `partition_html` sometimes.
* Fix several issues with the `requires_dependencies` decorator, including the error message
  and how it was used, which had caused an error for `unstructured-ingest --github-url ...`.

## 0.5.0

### Enhancements

* Add `requires_dependencies` Python decorator to check dependencies are installed before
  instantiating a class or running a function

### Features

* Added Wikipedia connector for ingest cli.

### Fixes

* Fix `process_document` file cleaning on failure
* Fixes an error introduced in the metadata tracking commit that caused `NarrativeText`
  and `FigureCaption` elements to be represented as `Text` in HTML documents.

## 0.4.16

### Enhancements

* Fallback to using file extensions for filetype detection if `libmagic` is not present

### Features

* Added setup script for Ubuntu
* Added GitHub connector for ingest cli.
* Added `partition_md` partitioner.
* Added Reddit connector for ingest cli.

### Fixes

* Initializes connector properly in ingest.main::MainProcess
* Restricts version of unstructured-inference to avoid multithreading issue

## 0.4.15

### Enhancements

* Added `elements_to_json` and `elements_from_json` for easier serialization/deserialization
* `convert_to_dict`, `dict_to_elements` and `convert_to_csv` are now aliases for functions
  that use the ISD terminology.

### Fixes

* Update to ensure all elements are preserved during serialization/deserialization

## 0.4.14

* Automatically install `nltk` models in the `tokenize` module.

## 0.4.13

* Fixes unstructured-ingest cli.

## 0.4.12

* Adds console_entrypoint for unstructured-ingest, other structure/doc updates related to ingest.
* Add `parser` parameter to `partition_html`.

## 0.4.11

* Adds `partition_doc` for partitioning Word documents in `.doc` format. Requires `libreoffice`.
* Adds `partition_ppt` for partitioning PowerPoint documents in `.ppt` format. Requires `libreoffice`.

## 0.4.10

* Fixes `ElementMetadata` so that it's JSON serializable when the filename is a `Path` object.

## 0.4.9

* Added ingest modules and s3 connector, sample ingest script
* Default to `url=None` for `partition_pdf` and `partition_image`
* Add ability to skip English specific check by setting the `UNSTRUCTURED_LANGUAGE` env var to `""`.
* Document `Element` objects now track metadata

## 0.4.8

* Modified XML and HTML parsers not to load comments.

## 0.4.7

* Added the ability to pull an HTML document from a url in `partition_html`.
* Added the the ability to get file summary info from lists of filenames and lists
  of file contents.
* Added optional page break to `partition` for `.pptx`, `.pdf`, images, and `.html` files.
* Added `to_dict` method to document elements.
* Include more unicode quotes in `replace_unicode_quotes`.

## 0.4.6

* Loosen the default cap threshold to `0.5`.
* Add a `UNSTRUCTURED_NARRATIVE_TEXT_CAP_THRESHOLD` environment variable for controlling
  the cap ratio threshold.
* Unknown text elements are identified as `Text` for HTML and plain text documents.
* `Body Text` styles no longer default to `NarrativeText` for Word documents. The style information
  is insufficient to determine that the text is narrative.
* Upper cased text is lower cased before checking for verbs. This helps avoid some missed verbs.
* Adds an `Address` element for capturing elements that only contain an address.
* Suppress the `UserWarning` when detectron is called.
* Checks that titles and narrative test have at least one English word.
* Checks that titles and narrative text are at least 50% alpha characters.
* Restricts titles to a maximum word length. Adds a `UNSTRUCTURED_TITLE_MAX_WORD_LENGTH`
  environment variable for controlling the max number of words in a title.
* Updated `partition_pptx` to order the elements on the page

## 0.4.4

* Updated `partition_pdf` and `partition_image` to return `unstructured` `Element` objects
* Fixed the healthcheck url path when partitioning images and PDFs via API
* Adds an optional `coordinates` attribute to document objects
* Adds `FigureCaption` and `CheckBox` document elements
* Added ability to split lists detected in `LayoutElement` objects
* Adds `partition_pptx` for partitioning PowerPoint documents
* LayoutParser models now download from HugginfaceHub instead of DropBox
* Fixed file type detection for XML and HTML files on Amazone Linux

## 0.4.3

* Adds `requests` as a base dependency
* Fix in `exceeds_cap_ratio` so the function doesn't break with empty text
* Fix bug in `_parse_received_data`.
* Update `detect_filetype` to properly handle `.doc`, `.xls`, and `.ppt`.

## 0.4.2

* Added `partition_image` to process documents in an image format.
* Fixed utf-8 encoding error in `partition_email` with attachments for `text/html`

## 0.4.1

* Added support for text files in the `partition` function
* Pinned `opencv-python` for easier installation on Linux

## 0.4.0

* Added generic `partition` brick that detects the file type and routes a file to the appropriate
  partitioning brick.
* Added a file type detection module.
* Updated `partition_html` and `partition_eml` to support file-like objects in 'rb' mode.
* Cleaning brick for removing ordered bullets `clean_ordered_bullets`.
* Extract brick method for ordered bullets `extract_ordered_bullets`.
* Test for `clean_ordered_bullets`.
* Test for `extract_ordered_bullets`.
* Added `partition_docx` for pre-processing Word Documents.
* Added new REGEX patterns to extract email header information
* Added new functions to extract header information `parse_received_data` and `partition_header`
* Added new function to parse plain text files `partition_text`
* Added new cleaners functions `extract_ip_address`, `extract_ip_address_name`, `extract_mapi_id`, `extract_datetimetz`
* Add new `Image` element and function to find embedded images `find_embedded_images`
* Added `get_directory_file_info` for summarizing information about source documents

## 0.3.5

* Add support for local inference
* Add new pattern to recognize plain text dash bullets
* Add test for bullet patterns
* Fix for `partition_html` that allows for processing `div` tags that have both text and child
  elements
* Add ability to extract document metadata from `.docx`, `.xlsx`, and `.jpg` files.
* Helper functions for identifying and extracting phone numbers
* Add new function `extract_attachment_info` that extracts and decodes the attachment
of an email.
* Staging brick to convert a list of `Element`s to a `pandas` dataframe.
* Add plain text functionality to `partition_email`

## 0.3.4

* Python-3.7 compat

## 0.3.3

* Removes BasicConfig from logger configuration
* Adds the `partition_email` partitioning brick
* Adds the `replace_mime_encodings` cleaning bricks
* Small fix to HTML parsing related to processing list items with sub-tags
* Add `EmailElement` data structure to store email documents

## 0.3.2

* Added `translate_text` brick for translating text between languages
* Add an `apply` method to make it easier to apply cleaners to elements

## 0.3.1

* Added \_\_init.py\_\_ to `partition`

## 0.3.0

* Implement staging brick for Argilla. Converts lists of `Text` elements to `argilla` dataset classes.
* Removing the local PDF parsing code and any dependencies and tests.
* Reorganizes the staging bricks in the unstructured.partition module
* Allow entities to be passed into the Datasaur staging brick
* Added HTML escapes to the `replace_unicode_quotes` brick
* Fix bad responses in partition_pdf to raise ValueError
* Adds `partition_html` for partitioning HTML documents.

## 0.2.6

* Small change to how \_read is placed within the inheritance structure since it doesn't really apply to pdf
* Add partitioning brick for calling the document image analysis API

## 0.2.5

* Update python requirement to >=3.7

## 0.2.4

* Add alternative way of importing `Final` to support google colab

## 0.2.3

* Add cleaning bricks for removing prefixes and postfixes
* Add cleaning bricks for extracting text before and after a pattern

## 0.2.2

* Add staging brick for Datasaur

## 0.2.1

* Added brick to convert an ISD dictionary to a list of elements
* Update `PDFDocument` to use the `from_file` method
* Added staging brick for CSV format for ISD (Initial Structured Data) format.
* Added staging brick for separating text into attention window size chunks for `transformers`.
* Added staging brick for LabelBox.
* Added ability to upload LabelStudio predictions
* Added utility function for JSONL reading and writing
* Added staging brick for CSV format for Prodigy
* Added staging brick for Prodigy
* Added ability to upload LabelStudio annotations
* Added text_field and id_field to stage_for_label_studio signature

## 0.2.0

* Initial release of unstructured
