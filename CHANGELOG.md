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
