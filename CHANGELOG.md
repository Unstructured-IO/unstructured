## 0.6.2-dev2

### Enhancements

* Added logic to `partition_pdf` for detecting copy protected PDFs and falling back
  to the hi res strategy when necessary.

### Features

* Add `partition_via_api` for partitioning documents through the hosted API.

### Fixes

* Fix how `exceeds_cap_ratio` handles empty (returns `True` instead of `False`)

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
