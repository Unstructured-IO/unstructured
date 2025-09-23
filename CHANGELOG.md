## 0.18.16-dev0

### Enhancement
- Speed up function _assign_hash_ids by 34% (codeflash)

## 0.18.15

### Enhancements
- Speed up function ElementHtml._get_children_html by 234% (codeflash)
- Speed up function group_broken_paragraphs by 30% (codeflash)

### Features

### Fixes

- Bumped dddependencies via pip-compile to address the crit CVE in:
  - deepdiff: 8.6.0 -> 8.6.1: GHSA-mw26-5g2v-hqw3
    
## 0.18.14

### Enhancements
- Speed up function sentence_count by 59% (codeflash)
- Speed up function `check_for_nltk_package` by 111% (codeflash)
- Speed up function `under_non_alpha_ratio` by 76% (codeflash)

### Features

### Fixes

- **change short text language detection log to debug** reduce warning level log spamming
  - Bumped dependencies via pip-compile to address the following CVEs:
    - **Python 3.12/3.13**: CVE-2025-8194, GHSA-v594-44hm-2j7p
    - **glibc & related (glibc, glibc-locale-posix, ld-linux, libcrypt1)**: CVE-2025-8058, GHSA-8xjp-c72j-67q8
    - **aiohttp**: GHSA-9548-qrrj-x5pj
    - **openjpeg**: CVE-2025-54874
    - **pypdf**: GHSA-7hfw-26vp-jp8m
    - **transformers**: GHSA-9356-575x-2w9m
    - **urllib3**: GHSA-48p4-8xcf-vxj5

## 0.18.13

### Enhancements

### Features

### Fixes

- **Parse a wider variety of date formats in email headers** The `partition_email` function is now more robust to non-standard date formats, including ISO-8601 dates with "Z" suffixes. This prevents `ValueError` exceptions when partitioning emails with these date formats.

## 0.18.12

### Enhancements

### Features

### Fixes
- **Prevent large file content in encoding exceptions** Replace UnicodeDecodeError with UnprocessableEntityError in encoding detection to avoid storing entire file content in exception objects, which can cause issues in logging and error reporting systems when processing large files.

## 0.18.11

### Enhancements
- **Standardized on `charset-normalizer` library for encoding detection** Previously we had both `chardet` and `charset-normalizer` as dependencies. We are dropping `chardet` and only using `charset-normalizer`.

### Features
- **Type-aware `<input>` mapping in HTML transformations** Bare `<input>` elements are now classified by their `type` attribute (checkbox → Checkbox, radio → RadioButton, others → FormFieldValue).


### Fixes
- **Recognize '|' as a delimiter** csv parser will now recognize '|' as a delimiter in addition to ',' and ';'.

## 0.18.10

### Enhancements
- **Updated CodeQL** Updated CodeQL GHA to v3 from deprecated v2.

### Features
- **Add OCR_AGENT_CACHE_SIZE environment variable** Added configurable cache size for OCR agents to control memory usage.

### Fixes

## 0.18.9

### Enhancements

### Features
- **Convert elements to markdown for output** Added function to convert elements to markdown format for easy viewing.

### Fixes
- *Language detection nit** Handle empty text

## 0.18.8

### Enhancements

### Features

### Fixes
- **Properly handle password protected xlsx** - detect password protection on XLSX files and raise appropriate

## 0.18.7

### Enhancements

- **`text_as_html` for Table element now keeps both `input` and `img` tag's `class` attribute** Previously in partition HTML any tag inside a table is stripped of its `class` attribute. Now this attribute is preserved for both `input` and `img` tag in the table element's `metadata.text_as_html`.

### Features
- **Add language detection for PDFs** Add document and element level language detection to PDFs.

### Fixes

## 0.18.6

### Enhancements

### Features

### Fixes
- **Improved epub partition errors** EPUB partition will now produce new type of error on unprocessable files.
- **Fix type for serialized TableChunks** Use `TableChunk` for the string value of the field `type` when serializing elements of type `TableChunk`, rather than using the value `Table`.

## 0.18.5

### Enhancements

- **Bump dependencies and remove lingering Python 3.9 artifacts** Cleaned up some references to 3.9 that were left When we dropped Python 3.9 support.
- **`text_as_html` for Table element now keeps `img` tag's `class` attribute** Previously in partition HTML any tag inside a table is stripped of its `class` attribute. Now this attribute is preserved for `img` tag in the table element's `metadata.text_as_html`.

### Features

### Fixes
- **Improve markdown code block handling** Code blocks in markdown were previously being processed as embedded code instead of plain text.

## 0.18.4

### Enhancements

### Features

### Fixes
- **Increase CSV field limit** Addresses failures in partition for csv files with large fields

## 0.18.3

### Enhancements

### Features

### Fixes
- **Upgrade Pillow to 11.3.0** Addresses a high priority CVE

## 0.18.2

### Enhancements

### Features

### Fixes
- **Fixes empty HTML content** Previously, when the HTML content was empty, the partitioner would raise a TypeError: Invalid input object: NoneType. Now it will return an empty list of elements.
- **Failproof docx malformed or merged tables** This fix prevents docx file with complex or vertical merges or malformed tables from failing at `tc_at_grid_offset` and raised `ValueError: no tc element at grid_offset=X`.
- **partition_md can read special characters on non- utf-8 files** `partition_md` reads the file as utf-8 previously. Now it uses `read_txt_file` that reads file with detected encoding.
- xml code not getting escaped in a code block in a markdown file when in partition
- **Fixes parsing HTML header and footer** Previously header and footer texts are partitioned as `UncategorizedText` or as the nested structure like `Title`. Now they are properly partitioned as `Header` and `Footer` element types.

## 0.18.1

### Enhancements

### Features
- **Add DocumentData element type** This is helpful in scenarios where there is large data that does not make sense to represent across each element in the document.

### Fixes
- The `encoding` property of the `_CsvPartitioningContext` is now properly used.

## 0.18.0

### Enhancements

### Features
- Upgraded Python version to 3.12

### Fixes
- Fix type error when `result_file_type` is expected to be a `FileType` but is `None`
- Fix chunking for elements with None text that has AttributeError 'NoneType' object has no attribute 'strip'.
- Invalid elements IDs are not visible in VLM output. Parent-child hierarchy is now retrieved based on unstructured element ID, instead of id injected into HTML code of element.
- Fix bs4 deprecation warnings by updating `findAll()` with `find_all()`.

## 0.17.10
- Drop Python 3.9 support as it reaches EOL in October 2025
- Update pip-compile script to use Python 3.10 and newer
- Update all packages using pip-compile

## 0.17.9
- Patch various CVEs

## 0.17.8

### Enhancements
- **Bump `unstructured-inference` to `1.0.5`** It includes critical fix to ensure inference model initialization is thread safe

### Features

### Fixes

## 0.17.7

### Enhancements
- **Updated Docker file with ENV HF_HUB_OFFLINE=1 to prevent the contianer from trying to access the internet

### Features

### Fixes
- **Fix image extraction for PNG files.** When `extract_image_block_to_payload` is True, and the image is a PNG, we get a Pillow error. We need to remove the PNG transparency layer before saving the image.
- **Fix logger deprecation warning**: Replaced usage of `logger.warn` with `logger.warning` to comply with the Python logging standards.
- **Throw validation error when json is passed with invalid unstructured json

## 0.17.6

### Enhancements

### Features

### Fixes
- The sort_page_element() use the element id to sort the elements.
Two executions of the same code, on the same file, produce different results. The order of the elements is random.
This makes it impossible to write stable unit tests, for example, or to obtain reproducible results.
- **Do not use NLP to determine element types for extracted elements with hi_res.** This avoids extraneous Title elements in hi_res outputs. This only applies to *extracted* elements, meaning text objects that are found outside of Object Detection objects which get mapped to *inferred* elements. (*extracted* and *inferred* elements get merged together to form the list of `Element`s returned by `pdf_partition()`)
- Resolve open CVEs
- Properly handle the case when an element's `text` attribute is None


## 0.17.5

### Enhancements
- **Remove test and dev dependencies from docker image.** This reduces the docker image size slightly and reduces potential security vulnerabilities.

### Features

### Fixes
- **Removed out of date ubuntu Dockerfile.** The Dockerfile was out of date and non-functional.
- **Fix for 'PSSyntaxError' import error: "cannot import name 'PSSyntaxError' from 'pdfminer.pdfparser'"** PSSyntaxError needed to be imported from its source 'pdfminer.psexceptions'.

## 0.17.4

### Enhancements

### Features

### Fixes
- **Deprecate `stage_for_label_studio` and drop `label_studio_sdk` dependency.** This resolves a CVE due to the dependency on `label_studio_sdk`.

## 0.17.3

### Enhancements

### Features

### Fixes
- Resolve open CVEs

## 0.17.3-dev0

### Enhancements

### Features

### Fixes
- **Fixes wrong detection of office files** certain office files wrongly identified as .ZIP when office(.docx,.xlsx and .pptx) files containing files other than word/document.xml, xl/workbook.xml and ppt/presentation.xml respectively will now be identified correctly by looking for word/document\*.xml, xl/workbook\*.xml and ppt/presentation\*.xml

## 0.17.2

* Fix Image in a <div> tag is "UncategorizedText" with no .text

## 0.17.1

### Enhancements

- **Add image_url of images in html partitioner** `<img>` tags with non-data content include a new image_url metadata field with the content of the src attribute.

- **Use `lxml` instead of `bs4` to parse hOCR data.** `lxml` is much faster than `bs4` given the hOCR data format is regular (garanteed because it is programatically generated)

- **bump `numpy` to `>2`**. And upgrade `paddlepaddle`, `unstructured-paddleocr`, `onnx` so they are compatible with `numpy>2`.

### Features

### Fixes

## 0.17.0

### Enhancements

- **Add support for images in html partitioner** `<img>` tags will now be parsed as `Image` elements. When `extract_image_block_types` includes `Image` and `extract_image_block_to_payload`=True then the `image_base64` will be included for images that specify the base64 data (rather than url) as the source.

- **Use kwargs instead of env to specify `ocr_agent` and `table_ocr_agent`** for `hi_res` strategy.

- **stop using `PageLayout.elements` to save memory and cpu cost**. Now only use `PageLayout.elements_array` throughout the partition, except when `analysis=True` where the drawing logic still uses `elements`.

### Features

### Fixes

## 0.16.25

### Enhancements

### Features

### Fixes

- **Fixes filetype detection for jsons passed as byte streams** - Now it prioritizes magic mimetype prediction over file extension when detecting filetypes


## 0.16.24

### Enhancements

- **Support dynamic partitioner file type registration**. Use `create_file_type` to create new file type that can be handled
  in unstructured and `register_partitioner` to enable registering your own partitioner for any file type.

- **`extract_image_block_types` now also works for CamelCase elemenet type names**. Previously `NarrativeText` and similar CamelCase element types can't be extracted using the mentioned parameter in `partition`. Now figures for those elements can be extracted like `Image` and `Table` elements

- **use block matrix to reduce peak memory usage for pdf/image partition**.

### Features

- **Add JSON elements to HTML converter** - Converts JSON elements file into an HTML file.

### Fixes


## 0.16.23

### Enhancements

### Features

### Fixes

- **Fixes detect_filetype when SpooledTemporaryFile is passed**. Previously some random name would get assigned to the file and the function raised error.

## 0.16.22

### Enhancements

### Features

### Fixes

- **Fix open CVES in and bump dependencies**

## 0.16.21

### Enhancements
- **Use password** to load PDF with all modes

- **use vectorized logic to merge inferred and extracted layouts**. Using the new `LayoutElements` data structure and numpy library to refactor the layout merging logic to improve compute performance as well as making logic more clear

- **Add PDF Miner configuration** Now PDF Miner can be configured via `pdfminer_line_overlap`, `pdfminer_word_margin`, `pdfminer_line_margin` and `pdfminer_char_margin` parameters added to partition method.

### Features

### Fixes

- **Fix file type detection for NDJSON files** NDJSON files were being detected as JSON due to having the same mime-type.
- Base-image was updated to resolved CVEs, running pipline to manually build

## 0.16.20

### Enhancements

### Features

### Fixes
- **Fix a security issue where rst and org files could read files in the local filesystem**. Certain filetypes could 'include' or 'import' local files into their content, allowing partitioning of arbitrary files from the local filesystem. Partitioning of these files is now sandboxed.

## 0.16.19

### Enhancements

### Features

### Fixes
- **Fix a bug where table extraction is skipped when it shouldn't**. Pages with just one table as its content or starts with a table misses table extraction. The routing logic is now fixed.
- **Correct deprecated `ruff` invocation in `make tidy`**.  This will future-proof it or avoid surprises if someone happens to upgrade Ruff.
- **Remove upper bound constraint on python version** in setup.py. Python3.13 is not yet officially supported, but allow users to try.
- **Fixes removing HTML elements from the inside of table cells** in html partition v=2.0. The HTML partitioner now correctly preserves HTML elements from the inside of table cells.

## 0.16.17

### Enhancements
- **Refactoring the VoyageAI integration** to use voyageai package directly, allowing extra features.

### Features

### Fixes
- **Fix a bug where `build_layout_elements_from_cor_regions` incorrectly joins texts in wrong order**.

## 0.16.16

### Enhancements

### Features
- **Vectorize layout (inferred, extracted, and OCR) data structure** Using `np.ndarray` to store a group of layout elements or text regions instead of using a list of objects. This improves the memory efficiency and compute speed around layout merging and deduplication.

### Fixes
- **Add auto-download for NLTK for Python Enviroment** When user import tokenize, It will  automatic download nltk data from `tokenize.py` file. Added `AUTO_DOWNLOAD_NLTK` flag in `tokenize.py` to download `NLTK_DATA`.
- **Correctly patch pdfminer to avoid PDF repair**. The patch applied to pdfminer's parser caused it to occasionally split tokens in content streams, throwing `PDFSyntaxError`.  Repairing these PDFs sometimes failed (since they were not actually invalid) resulting in unnecessary OCR fallback.
- **Drop usage of ndjson dependency**

## 0.16.15
### Enhancements

### Features

### Fixes
- **Update `unstructured-inference`** to 0.8.6 in requirements which removed `layoutparser` dependency libs
- **Update `pdfminer-six` to 20240706**

## 0.16.14

### Enhancements

### Features

### Fixes
- **Fix an issue with multiple values for `infer_table_structure`** when paritioning email with image attachements the kwarg calls into `partition` to partition the image already contains `infer_table_structure`. Now `partition` function checks if the `kwarg` has `infer_table_structure` already

## 0.16.13

### Enhancements
- **Add character-level filtering for tesseract output**. It is controllable via `TESSERACT_CHARACTER_CONFIDENCE_THRESHOLD` environment variable.

### Features

### Fixes

- **Fix NLTK Download** to use nltk assets in docker image
- removed the ability to automatically download nltk package if missing

## 0.16.12

### Enhancements

- **Prepare auto-partitioning for pluggable partitioners**. Move toward a uniform partitioner call signature so a custom or override partitioner can be registered without code changes.
- **Add NDJSON file type support.**

### Features

### Fixes

- **Base image has been updated.**
- **Upgrade ruff to latest.** Previously the ruff version was pinned to <0.5. Remove that pin and fix the handful of lint items that resulted.
- **CSV with asserted XLS content-type is correctly identified as CSV.** Resolves a bug where a CSV file with an asserted content-type of `application/vnd.ms-excel` was incorrectly identified as an XLS file.
- **Improve element-type mapping for Chinese text.** Fixes bug where Chinese text would produce large numbers of false-positive `Title` elements.
- **Improve element-type mapping for HTML.** Fixes bug where certain non-title elements were classified as `Title`.

## 0.16.11

### Enhancements

- **Enhance quote standardization tests** with additional Unicode scenarios
- **Relax table segregation rule in chunking.** Previously a `Table` element was always segregated into its own pre-chunk such that the `Table` appeared alone in a chunk or was split into multiple `TableChunk` elements, but never combined with `Text`-subtype elements. Allow table elements to be combined with other elements in the same chunk when space allows.
- **Compute chunk length based solely on `element.text`.** Previously `.metadata.text_as_html` was also considered and since it is always longer that the text (due to HTML tag overhead) it was the effective length criterion. Remove text-as-html from the length calculation such that text-length is the sole criterion for sizing a chunk.

### Features

### Fixes

- Fix ipv4 regex to correctly include up to three digit octets.

## 0.16.10

### Enhancements

### Features

### Fixes

- **Fix original file doctype detection** from cct converted file paths for metrics calculation.

## 0.16.9

### Enhancements

### Features

### Fixes

- **Fix NLTK Download** to not download from unstructured S3 Bucket

## 0.16.8

### Enhancements
- **Metrics: Weighted table average is optional**

### Features

### Fixes

## 0.16.7

### Enhancements
- **Add image_alt_mode to partition_html** Adds an `image_alt_mode` parameter to `partition_html()` to control how alt text is extracted from images in HTML documents for `html_parser_version=v2` . The parameter can be set to `to_text` to extract alt text as text from `<img>` html tags

### Features

### Fixes


## 0.16.6

### Enhancements
- **Every `<table>` tag is considered to be ontology.Table** Added special handling for tables in HTML partitioning (`html_parser_version=v2`. This change is made to improve the accuracy of table extraction from HTML documents.
- **Every HTML has default ontology class assigned** When parsing HTML with `html_parser_version=v2` to ontology each defined HTML in the Ontology has assigned default ontology class. This way it is possible to assign ontology class instead of UncategorizedText when the HTML tag is predicted correctly without class assigned class
- **Use (number of actual table) weighted average for table metrics** In evaluating table metrics the mean aggregation now uses the actual number of tables in a document to weight the metric scores

### Features

### Fixes
- **ElementMetadata consolidation** Now `text_as_html` metadata is combined across all elements in CompositeElement when chunking HTML output

## 0.16.5

### Enhancements

### Features

### Fixes
- **Fixes parsing HTML v2 parser** Now max recursion limit is set and value is correctly extracted from ontology element


## 0.16.4

### Enhancements

* **`value` attribute in `<input/>` element is parsed to `OntologyElement.text` in ontology**
* **`id` and `class` attributes removed from Table subtags in HTML partitioning**
* **cleaned `to_html` and newly introduced `to_text` in `OntologyElement`**
* **Elements created from V2 HTML are less granular** Added merging of adjacent text elements and inline html tags in the HTML partitioner to reduce the number of elements created from V2 HTML.

### Features

* **Add support for link extraction in pdf hi_res strategy.** The `partition_pdf()` function now supports link extraction when using the `hi_res` strategy, allowing users to extract hyperlinks from PDF documents more effectively.

### Fixes


## 0.16.3

### Enhancements

### Features

### Fixes

* **V2 elements without first parent ID can be parsed**
* **Fix missing elements when layout element parsed in V2 ontology**
* updated **unstructured-inference** to be **0.8.1** in requirements/extra-pdf-image.in


## 0.16.2

### Enhancements

### Features

* **Whitespace-invariant CCT distance metric.** CCT Levenshtein distance for strings is by default computed with standardized whitespaces.

### Fixes

* **Fixed retry config settings for partition_via_api function** If the SDK's default retry config is not set the retry config getter function does not fail anymore.

## 0.16.1

### Enhancements

* **Bump `unstructured-inference` to 0.7.39** and upgrade other dependencies
* **Round coordinates** Round coordinates when computing bounding box overlaps in `pdfminer_processing.py` to nearest machine precision. This can help reduce underterministic behavior from machine precision that affects which bounding boxes to combine.
* **Request retry parameters in `partition_via_api` function.** Expose retry-mechanism related parameters in the `partition_via_api` function to allow users to configure the retry behavior of the API requests.

### Features

* **Parsing HTML to Unstructured Elements and back**

### Fixes

* **Remove unsupported chipper model**
* **Rewrite of `partition.email` module and tests.** Use modern Python stdlib `email` module interface to parse email messages and attachments. This change shortens and simplifies the code, and makes it more robust and maintainable. Several historical problems were remedied in the process.
* **Minify text_as_html from DOCX.** Previously `.metadata.text_as_html` for DOCX tables was "bloated" with whitespace and noise elements introduced by `tabulate` that produced over-chunking and lower "semantic density" of elements. Reduce HTML to minimum character count while preserving all text.
* **Fall back to filename extension-based file-type detection for unidentified OLE files.** Resolves a problem where a DOC file that could not be detected as such by `filetype` was incorrectly identified as a MSG file.
* **Minify text_as_html from XLSX.** Previously `.metadata.text_as_html` for DOCX tables was "bloated" with whitespace and noise elements introduced by `pandas` that produced over-chunking and lower "semantic density" of elements. Reduce HTML to minimum character count while preserving all text.
* **Minify text_as_html from CSV.** Previously `.metadata.text_as_html` for CSV tables was "bloated" with whitespace and noise elements introduced by `pandas` that produced over-chunking and lower "semantic density" of elements. Reduce HTML to minimum character count while preserving all text.
* **Minify text_as_html from PPTX.** Previously `.metadata.text_as_html` for PPTX tables was "bloated" with whitespace and noise elements introduced by `tabulate` that produced over-chunking and lower "semantic density" of elements. Reduce HTML to minimum character count while preserving all text and structure.

## 0.16.0

### Enhancements

* **Remove ingest implementation.** The deprecated ingest functionality has been removed, as it is now maintained in the separate [unstructured-ingest](https://github.com/Unstructured-IO/unstructured-ingest) repository.
  * Replace extras in `requirements/ingest` directory with a new `ingest.txt` extra for installing the `unstructured-ingest` library.
  * Remove the `unstructured.ingest` submodule.
  * Delete all shell scripts previously used for destination ingest tests.

### Features

### Fixes

* **Add language parameter to `OCRAgentGoogleVision`.**  Introduces an optional language parameter in the `OCRAgentGoogleVision` constructor to serve as a language hint for `document_text_detection`. This ensures compatibility with the OCRAgent's `get_instance` method and resolves errors when parsing PDFs with Google Cloud Vision as the OCR agent.

## 0.15.14

### Enhancements

### Features

* **Add (but do not install) a new post-partitioning decorator to handle metadata added for all file-types, like `.filename`, `.filetype` and `.languages`.** This will be installed in a closely following PR to replace the four currently being used for this purpose.

### Fixes

* **Update Python SDK usage in `partition_via_api`.** Make a minor syntax change to ensure forward compatibility with the upcoming 0.26.0 Python SDK.
* **Remove "unused" `date_from_file_object` parameter.** As part of simplifying partitioning parameter set, remove `date_from_file_object` parameter. A file object does not have a last-modified date attribute so can never give a useful value. When a file-object is used as the document source (such as in Unstructured API) the last-modified date must come from the `metadata_last_modified` argument.
* **Fix occasional `KeyError` when mapping parent ids to hash ids.** Occasionally the input elements into `assign_and_map_hash_ids` can contain duplicated element instances, which lead to error when mapping parent id.
* **Allow empty text files.** Fixes an issue where text files with only white space would fail to be partitioned.
* **Remove double-decoration for CSV, DOC, ODT partitioners.** Refactor these partitioners to use the new `@apply_metadata()` decorator and only decorate the principal partitioner (CSV and DOCX in this case); remove decoration from delegating partitioners.
* **Remove double-decoration for PPTX, TSV, XLSX, and XML partitioners.** Refactor these partitioners to use the new `@apply_metadata()` decorator and only decorate the principal partitioner; remove decoration from delegating partitioners.
* **Remove double-decoration for HTML, EPUB, MD, ORG, RST, and RTF partitioners.** Refactor these partitioners to use the new `@apply_metadata()` decorator and only decorate the principal partitioner (HTML in this case); remove decoration from delegating partitioners.
* **Remove obsolete min_partition/max_partition args from TXT and EML.** The legacy `min_partition` and `max_partition` parameters were an initial rough implementation of chunking but now interfere with chunking and are unused. Remove those parameters from `partition_text()` and `partition_email()`.
* **Remove double-decoration on EML and MSG.** Refactor these partitioners to rely on the new `@apply_metadata()` decorator operating on partitioners they delegate to (TXT, HTML, and all others for attachments) and remove direct decoration from EML and MSG.
* **Remove double-decoration for PPT.** Remove decorators from the delegating PPT partitioner.
* **Quick-fix CI error in auto test-filetype.** Better fix to follow shortly.

## 0.15.13

### BREAKING CHANGES

* **Remove dead experimental code.** Unused code in `file_utils.experimental` and `file_utils.metadata` was removed. These functions were never published in the documentation, but if a client dug these out and used them this removal could break client code.

### Enhancements

* **Improve `pdfminer` image cleanup process**. Optimized the removal of duplicated pdfminer images by performing the cleanup before merging elements, rather than after. This improvement reduces execution time and enhances overall processing speed of PDF documents.

### Features

### Fixes

* **Fixes high memory overhead for intersection area computation** Using `numpy.float32` for coordinates and remove intermediate variables to reduce memory usage when computing intersection areas
* **Fixes the `arm64` image build** `arm64` builds are now fixed and will be available against starting with the `0.15.13` release.

## 0.15.12

### Enhancements

* **Improve `pdfminer` element processing** Implemented splitting of `pdfminer` elements (groups of text chunks) into smaller bounding boxes (text lines). This prevents loss of information from the object detection model and facilitates more effective removal of duplicated `pdfminer` text.

### Features

### Fixes

* **Fixed table accuracy metric** Table accuracy was incorrectly using column content difference in calculating row accuracy.

## 0.15.11

### Enhancements

* **Add deprecation warning to embed code**
* **Remove ingest console script**

## 0.15.10

### Enhancements

* **Enhance `pdfminer` element cleanup** Expand removal of `pdfminer` elements to include those inside all `non-pdfminer` elements, not just `tables`.
* **Modified analysis drawing tools to dump to files and draw from dumps** If the parameter `analysis` of the `partition_pdf` function is set to `True`, the layout for Object Detection, Pdfminer Extraction, OCR and final layouts will be dumped as json files. The drawers now accept dict (dump) objects instead of internal classes instances.
* **Vectorize pdfminer elements deduplication computation**. Use `numpy` operations to compute IOU and sub-region membership instead of using simply loop. This improves the speed of deduplicating elements for pages with a lot of elements.

### Features

### Fixes

## 0.15.9

### Enhancements

### Features

* **Add support for encoding parameter in partition_csv**

### Fixes

* **Check storage contents for OLE file type detection** Updates `detect_filetype` to check the content of OLE files to more reliable differentiate DOC, PPT, XLS, and MSG files. As part of this, the `"msg"` extra was removed because the `python-oxmsg` package is now a base dependency.
* **Fix disk space leaks and Windows errors when accessing file.name on a NamedTemporaryFile** Uses of `NamedTemporaryFile(..., delete=False)` and/or uses of `file.name` of NamedTemporaryFiles have been replaced with TemporaryFileDirectory to avoid a known issue: https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile

## 0.15.8

### Enhancements

* **Bump unstructured.paddleocr to 2.8.1.0.**

### Features

* **Add MixedbreadAI embedder** Adds MixedbreadAI embeddings to support embedding via Mixedbread AI.

### Fixes

* **Replace `pillow-heif` with `pi-heif`**. Replaces `pillow-heif` with `pi-heif` due to more permissive licensing on the wheel for `pi-heif`.
* **Minify text_as_html from DOCX.** Previously `.metadata.text_as_html` for DOCX tables was "bloated" with whitespace and noise elements introduced by `tabulate` that produced over-chunking and lower "semantic density" of elements. Reduce HTML to minimum character count without preserving all text.
* **Fall back to filename extension-based file-type detection for unidentified OLE files.** Resolves a problem where a DOC file that could not be detected as such by `filetype` was incorrectly identified as a MSG file.

## 0.15.7

### Enhancements

### Features

### Fixes

* **Fix NLTK data download path to prevent nested directories**. Resolved an issue where a nested "nltk_data" directory was created within the parent "nltk_data" directory when it already existed. This fix prevents errors in checking for existing downloads and loading models from NLTK data.

## 0.15.6

### Enhancements

### Features

### Fixes

* **Bump to NLTK 3.9.x** Bumps to the latest `nltk` version to resolve CVE.
* **Update CI for `ingest-test-fixture-update-pr` to resolve NLTK model download errors.**
* **Synchronized text and html on `TableChunk` splits.** When a `Table` element is divided during chunking to fit the chunking window, `TableChunk.text` corresponds exactly with the table text in `TableChunk.metadata.text_as_html`, `.text_as_html` is always parseable HTML, and the table is split on even row boundaries whenever possible.

## 0.15.5

### Enhancements

### Features

### Fixes

* **Revert to using `unstructured.pytesseract` fork**. Due to the unavailability of some recent release versions of `pytesseract` on PyPI, the project now uses the `unstructured.pytesseract` fork to ensure stability and continued support.
* **Bump `libreoffice` verson in image.** Bumps the `libreoffice` version to `25.2.5.2` to address CVEs.
* **Downgrade NLTK dependency version for compatibility**. Due to the unavailability of `nltk==3.8.2` on PyPI, the NLTK dependency has been downgraded to `<3.8.2`. This change ensures continued functionality and compatibility.

## 0.15.4

### Enhancements

### Features

### Fixes

* **Resolve an installation error with `pytesseract>=0.3.12` that occurred during `pip install unstructured[pdf]==0.15.3`.**

## 0.15.3

### Enhancements

### Features

### Fixes

* **Remove the custom index URL from `extra-paddleocr.in` to resolve the error in the `setup.py` configuration.**

## 0.15.2

### Enhancements

* **Improve directory handling when extracting image blocks**. The `figures` directory is no longer created when the `extract_image_block_to_payload` parameter is set to `True`.

### Features

* **Added per-class Object Detection metrics in the evaluation**. The metrics include average precision, precision, recall, and f1-score for each class in the dataset.

### Fixes

* **Updates NLTK data file for compatibility with `nltk>=3.8.2`**. The NLTK data file now container `punkt_tab`, making it possible to upgrade to `nltk>=3.8.2`. The `nltk==3.8.2` patches CVE-2024-39705.
* **Renames Astra to Astra DB** Conforms with DataStax internal naming conventions.
* **Accommodate single-column CSV files.** Resolves a limitation of `partition_csv()` where delimiter detection would fail on a single-column CSV file (which naturally has no delimeters).
* **Accommodate `image/jpg` in PPTX as alias for `image/jpeg`.** Resolves problem partitioning PPTX files having an invalid `image/jpg` (should be `image/jpeg`) MIME-type in the `[Content_Types].xml` member of the PPTX Zip archive.
* **Fixes an issue in Object Detection metrics** The issue was in preprocessing/validating the ground truth and predicted data for object detection metrics.
* **Removes dependency on unstructured.pytesseract** Unstructured forked pytesseract while waiting for code to be upstreamed. Now that the new version has been released, this fork can be removed.

## 0.15.1

### Enhancements

* **Improve `pdfminer` embedded `image` extraction to exclude text elements and produce more accurate bounding boxes.** This results in cleaner, more precise element extraction in `pdf` partitioning.

### Features

* **Update partition_eml and partition_msg to capture cc, bcc, and message_id fields** Cc, bcc, and message_id information is captured in element metadata for both msg and email partitioning and `Recipient` elements are generated for cc and bcc when `include_headers=True` for email partitioning.
* **Mark ingest as deprecated** Begin sunset of ingest code in this repo as it's been moved to a dedicated repo.
* **Add `pdf_hi_res_max_pages` argument for partitioning, which allows rejecting PDF files that exceed this page number limit, when the `high_res` strategy is chosen.** By default, it will allow parsing PDF files with an unlimited number of pages.

### Fixes

* **Update `HuggingFaceEmbeddingEncoder` to use `HuggingFaceEmbeddings` from `langchain_huggingface` package instead of the deprecated version from `langchain-community`.** This resolves the deprecation warning and ensures compatibility with future versions of langchain.
* **Update `OpenAIEmbeddingEncoder` to use `OpenAIEmbeddings` from `langchain-openai` package instead of the deprecated version from `langchain-community`.** This resolves the deprecation warning and ensures compatibility with future versions of langchain.
* **Update import of Pinecone exception** Adds compatibility for pinecone-client>=5.0.0
* **File-type detection catches non-existent file-path.** `detect_filetype()` no longer silently falls back to detecting a file-type based on the extension when no file exists at the path provided. Instead `FileNotFoundError` is raised. This provides consistent user notification of a mis-typed path rather than an unpredictable exception from a file-type specific partitioner when the file cannot be opened.
* **EML files specified as a file-path are detected correctly.** Resolved a bug where an EML file submitted to `partition()` as a file-path was identified as TXT and partitioned using `partition_text()`. EML files specified by path are now identified and processed correctly, including processing any attachments.
* **A DOCX, PPTX, or XLSX file specified by path and ambiguously identified as MIME-type "application/octet-stream" is identified correctly.** Resolves a shortcoming where a file specified by path immediately fell back to filename-extension based identification when misidentified as "application/octet-stream", either by asserted content type or a mis-guess by libmagic. An MS Office file misidentified in this way is now correctly identified regardless of its filename and whether it is specified by path or file-like object.
* **Textual content retrieved from a URL with gzip transport compression now partitions correctly.** Resolves a bug where a textual file-type (such as Markdown) retrieved by passing a URL to `partition()` would raise when `gzip` compression was used for transport by the server.
* **A DOCX, PPTX, or XLSX content-type asserted on partition is confirmed or fixed.** Resolves a bug where calling `partition()` with a swapped MS-Office `content_type` would cause the file-type to be misidentified. A DOCX, PPTX, or XLSX MIME-type received by `partition()` is now checked for accuracy and corrected if the file is for a different MS-Office 2007+ type.
* **DOC, PPT, XLS, and MSG files are now auto-detected correctly.** Resolves a bug where DOC, PPT, and XLS files were auto-detected as MSG files under certain circumstances.

## 0.15.0

### Enhancements

* **Improve text clearing process in email partitioning.** Updated the email partitioner to remove both `=\n` and `=\r\n` characters during the clearing process. Previously, only `=\n` characters were removed.
* **Bump unstructured.paddleocr to 2.8.0.1.**
* **Refine HTML parser to accommodate block element nested in phrasing.** HTML parser no longer raises on a block element (e.g. `<p>`, `<div>`) nested inside a phrasing element (e.g. `<strong>` or `<cite>`). Instead it breaks the phrasing run (and therefore element) at the block-item start and begins a new phrasing run after the block-item. This is consistent with how the browser determines element boundaries in this situation.
* **Install rewritten HTML parser to fix 12 existing bugs and provide headroom for refinement and growth.** A rewritten HTML parser resolves a collection of outstanding bugs with HTML partitioning and provides a firm foundation for further elaborating that important partitioner.
* **CI check for dependency licenses** Adds a CI check to ensure dependencies are appropriately licensed.

### Features

* **Add support for specifying OCR language to `partition_pdf()`.** Extend language specification capability to `PaddleOCR` in addition to `TesseractOCR`. Users can now specify OCR languages for both OCR engines when using `partition_pdf()`.
* **Add AstraDB source connector** Adds support for ingesting documents from AstraDB.

### Fixes

* **Remedy error on Windows when `nltk` binaries are downloaded.** Work around a quirk in the Windows implementation of `tempfile.NamedTemporaryFile` where accessing the temporary file by name raises `PermissionError`.
* **Move Astra embedded_dimension to write config**

## 0.14.10

### Enhancements

* **Update unstructured-client dependency** Change unstructured-client dependency pin back to greater than min version and updated tests that were failing given the update.
* **`.doc` files are now supported in the `arm64` image.**. `libreoffice24` is added to the `arm64` image, meaning `.doc` files are now supported. We have follow on work planned to investigate adding `.ppt` support for `arm64` as well.
* **Add table detection metrics: recall, precision and f1.**
* **Remove unused _with_spans metrics.**

### Features

**Add Object Detection Metrics to CI** Add object detection metrics (average precision, precision, recall and f1-score) implementations.

### Fixes

* **Fix counting false negatives and false positives in table structure evaluation.**
* **Fix Slack CI test** Change channel that Slack test is pointing to because previous test bot expired
* **Remove NLTK download** Removes `nltk.download` in favor of downloading from an S3 bucket we host to mitigate CVE-2024-39705

## 0.14.9

### Enhancements

* **Added visualization and OD model result dump for PDF** In PDF `hi_res` strategy the `analysis` parameter can be used to visualize the result of the OD model and dump the result to a file. Additionally, the visualization of bounding boxes of each layout source is rendered and saved for each page.
* **`partition_docx()` distinguishes "file not found" from "not a ZIP archive" error.** `partition_docx()` now provides different error messages for "file not found" and "file is not a ZIP archive (and therefore not a DOCX file)". This aids diagnosis since these two conditions generally point in different directions as to the cause and fix.

### Features

### Fixes

* **Fix a bug where multiple `soffice` processes could be attempted** Add a wait mechanism in `convert_office_doc` so that the function first checks if another `soffice` is running already: if yes wait till the other process finishes or till the wait timeout before spawning a subprocess to run `soffice`
* **`partition()` now forwards `strategy` arg to `partition_docx()`, `partition_pptx()`, and their brokering partitioners for DOC, ODT, and PPT formats.** A `strategy` argument passed to `partition()` (or the default value "auto" assigned by `partition()`) is now forwarded to `partition_docx()`, `partition_pptx()`, and their brokering partitioners when those filetypes are detected.

## 0.14.8

### Enhancements

* **Move arm64 image to wolfi-base** The `arm64` image now runs on `wolfi-base`. The `arm64` build for `wolfi-base` does not yet include `libreoffce`, and so `arm64` does not currently support processing `.doc`, `.ppt`, or `.xls` file. If you need to process those files on `arm64`, use the legacy `rockylinux` image.

### Features

### Fixes

* **Bump unstructured-inference==0.7.36** Fix `ValueError` when converting cells to html.
* **`partition()` now forwards `strategy` arg to `partition_docx()`, `partition_ppt()`, and `partition_pptx()`.** A `strategy` argument passed to `partition()` (or the default value "auto" assigned by `partition()`) is now forwarded to `partition_docx()`, `partition_ppt()`, and `partition_pptx()` when those filetypes are detected.
* **Fix missing sensitive field markers** for embedders

## 0.14.7

### Enhancements

* **Pull from `wolfi-base` image.** The amd64 image now pulls from the `unstructured` `wolfi-base` image to avoid duplication of dependency setup steps.
* **Fix windows temp file.** Make the creation of a temp file in unstructured/partition/pdf_image/ocr.py windows compatible.

### Features

* **Expose conversion functions for tables** Adds public functions to convert tables from HTML to the Deckerd format and back
* **Adds Kafka Source and Destination** New source and destination connector added to all CLI ingest commands to support reading from and writing to Kafka streams. Also supports Confluent Kafka.

### Fixes

* **Fix an error publishing docker images.** Update user in docker-smoke-test to reflect changes made by the amd64 image pull from the "unstructured" "wolfi-base" image.
* **Fix a IndexError when partitioning a pdf with values for both `extract_image_block_types` and `starting_page_number`.

## 0.14.6

### Enhancements

* **Bump unstructured-inference==0.7.35** Fix syntax for generated HTML tables.

### Features

* **tqdm ingest support** add optional flag to ingest flow to print out progress bar of each step in the process.

### Fixes

* **Remove deprecated `overwrite_schema` kwarg from Delta Table connector.** The `overwrite_schema` kwarg is deprecated in `deltalake>=0.18.0`. `schema_mode=` should be used now instead. `schema_mode="overwrite"` is equivalent to `overwrite_schema=True` and `schema_mode="merge"` is equivalent to `overwrite_schema="False"`. `schema_mode` defaults to `None`. You can also now specify `engine`, which defaults to `"pyarrow"`. You need to specify `enginer="rust"` to use `"schema_mode"`.
* **Fix passing parameters to python-client** - Remove parsing list arguments to strings in passing arguments to python-client in Ingest workflow and `partition_via_api`
* **table metric bug fix** get_element_level_alignment()now will find all the matched indices in predicted table data instead of only returning the first match in the case of multiple matches for the same gt string.
* **fsspec connector path/permissions bug** V2 fsspec connectors were failing when defined relative filepaths had leading slash. This strips that slash to guarantee the relative path never has it.
* **Dropbox connector internal file path bugs** Dropbox source connector currently raises exceptions when indexing files due to two issues: a path formatting idiosyncrasy of the Dropbox library and a divergence in the definition of the Dropbox libraries fs.info method, expecting a 'url' parameter rather than 'path'.
* **update table metric evaluation to handle corrected HTML syntax for tables** This change is connected to the update in [unstructured-inference change](https://github.com/Unstructured-IO/unstructured-inference/pull/355) - fixes transforming HTML table to deckerd and internal cells format.

## 0.14.5

### Enhancements

* **Filtering for tar extraction** Adds tar filtering to the compression module for connectors to avoid decompression malicious content in `.tar.gz` files. This was added to the Python `tarfile` lib in Python 3.12. The change only applies when using Python 3.12 and above.
* **Use `python-oxmsg` for `partition_msg()`.** Outlook MSG emails are now partitioned using the `python-oxmsg` package which resolves some shortcomings of the prior MSG parser.

### Features

### Fixes

* **8-bit string Outlook MSG files are parsed.** `partition_msg()` is now able to parse non-unicode Outlook MSG emails.
* **Attachments to Outlook MSG files are extracted intact.** `partition_msg()` is now able to extract attachments without corruption.

## 0.14.4

### Enhancements

* **Move logger error to debug level when PDFminer fails to extract text** which includes error message for Invalid dictionary construct.
* **Add support for Pinecone serverless** Adds Pinecone serverless to the connector tests. Pinecone
  serverless will work version versions >=0.14.2, but hadn't been tested until now.

### Features

- **Allow configuration of the Google Vision API endpoint** Add an environment variable to select the Google Vision API in the US or the EU.

### Fixes

* **Address the issue of unrecognized tables in `UnstructuredTableTransformerModel`** When a table is not recognized, the `element.metadata.text_as_html` attribute is set to an empty string.
* **Remove root handlers in ingest logger**. Removes root handlers in ingest loggers to ensure secrets aren't accidentally exposed in Colab notebooks.
* **Fix V2 S3 Destination Connector authentication** Fixes bugs with S3 Destination Connector where the connection config was neither registered nor properly deserialized.
* **Clarified dependence on particular version of `python-docx`** Pinned `python-docx` version to ensure a particular method `unstructured` uses is included.
* **Ingest preserves original file extension** Ingest V2 introduced a change that dropped the original extension for upgraded connectors. This reverts that change.

## 0.14.3

### Enhancements

* **Move `category` field from Text class to Element class.**
* **`partition_docx()` now supports pluggable picture sub-partitioners.** A subpartitioner that accepts a DOCX `Paragraph` and generates elements is now supported. This allows adding a custom sub-partitioner that extracts images and applies OCR or summarization for the image.
* **Add VoyageAI embedder** Adds VoyageAI embeddings to support embedding via Voyage AI.

### Features

### Fixes

* **Fix `partition_pdf()` to keep spaces in the text**. The control character `\t` is now replaced with a space instead of being removed when merging inferred elements with embedded elements.
* **Turn off XML resolve entities** Sets `resolve_entities=False` for XML parsing with `lxml`
  to avoid text being dynamically injected into the XML document.
* **Add backward compatibility for the deprecated pdf_infer_table_structure parameter**.
* **Add the missing `form_extraction_skip_tables` argument to the `partition_pdf_or_image` call**.
  to avoid text being dynamically injected into the XML document.
* **Chromadb change from Add to Upsert using element_id to make idempotent**
* **Diable `table_as_cells` output by default** to reduce overhead in partition; now `table_as_cells` is only produced when the env `EXTACT_TABLE_AS_CELLS` is `true`
* **Reduce excessive logging** Change per page ocr info level logging into detail level trace logging
* **Replace try block in `document_to_element_list` for handling HTMLDocument** Use `getattr(element, "type", "")` to get the `type` attribute of an element when it exists. This is more explicit way to handle the special case for HTML documents and prevents other types of attribute error from being silenced by the try block

## 0.14.2

### Enhancements

* **Bump unstructured-inference==0.7.33**.

### Features

* **Add attribution to the `pinecone` connector**.

### Fixes

## 0.14.1

### Enhancements

* **Refactor code related to embedded text extraction**. The embedded text extraction code is moved from `unstructured-inference` to `unstructured`.

### Features

* **Large improvements to the ingest process:**
  * Support for multiprocessing and async, with limits for both.
  * Streamlined to process when mapping CLI invocations to the underlying code
  * More granular steps introduced to give better control over process (i.e. dedicated step to uncompress files already in the local filesystem, new optional staging step before upload)
  * Use the python client when calling the unstructured api for partitioning or chunking
  * Saving the final content is now a dedicated destination connector (local) set as the default if none are provided. Avoids adding new files locally if uploading elsewhere.
  * Leverage last modified date when deciding if new files should be downloaded and reprocessed.
  * Add attribution to the `pinecone` connector
  * **Add support for Python 3.12**. `unstructured` now works with Python 3.12!

### Fixes

## 0.14.0

### BREAKING CHANGES

* **Turn table extraction for PDFs and images off by default**. Reverting the default behavior for table extraction to "off" for PDFs and images. A number of users didn't realize we made the change and were impacted by slower processing times due to the extra model call for table extraction.

### Enhancements

* **Skip unnecessary element sorting in `partition_pdf()`**. Skip element sorting when determining whether embedded text can be extracted.
* **Faster evaluation** Support for concurrent processing of documents during evaluation
* **Add strategy parameter to `partition_docx()`.** Behavior of future enhancements may be sensitive the partitioning strategy. Add this parameter so `partition_docx()` is aware of the requested strategy.
* **Add GLOBAL_WORKING_DIR and GLOBAL_WORKING_PROCESS_DIR** configuration parameteres to control temporary storage.

### Features

* **Add form extraction basics (document elements and placeholder code in partition)**. This is to lay the ground work for the future. Form extraction models are not currently available in the library. An attempt to use this functionality will end in a `NotImplementedError`.

### Fixes

* **Add missing starting_page_num param to partition_image**
* **Make the filename and file params for partition_image and partition_pdf match the other partitioners**
* **Fix include_slide_notes and include_page_breaks params in partition_ppt**
* **Re-apply: skip accuracy calculation feature** Overwritten by mistake
* **Fix type hint for paragraph_grouper param** `paragraph_grouper` can be set to `False`, but the type hint did not not reflect this previously.
* **Remove links param from partition_pdf** `links` is extracted during partitioning and is not needed as a paramter in partition_pdf.
* **Improve CSV delimeter detection.** `partition_csv()` would raise on CSV files with very long lines.
* **Fix disk-space leak in `partition_doc()`.** Remove temporary file created but not removed when `file` argument is passed to `partition_doc()`.
* **Fix possible `SyntaxError` or `SyntaxWarning` on regex patterns.** Change regex patterns to raw strings to avoid these warnings/errors in Python 3.11+.
* **Fix disk-space leak in `partition_odt()`.** Remove temporary file created but not removed when `file` argument is passed to `partition_odt()`.
* **AstraDB: option to prevent indexing metadata**
* **Fix Missing py.typed**

## 0.13.7

### Enhancements

* **Remove `page_number` metadata fields** for HTML partition until we have a better strategy to decide page counting.
* **Extract OCRAgent.get_agent().** Generalize access to the configured OCRAgent instance beyond its use for PDFs.
* **Add calculation of table related metrics which take into account colspans and rowspans**
* **Evaluation: skip accuracy calculation** for files for which output and ground truth sizes differ greatly

### Features

* **add ability to get ratio of `cid` characters in embedded text extracted by `pdfminer`**.

### Fixes

* **`partition_docx()` handles short table rows.** The DOCX format allows a table row to start late and/or end early, meaning cells at the beginning or end of a row can be omitted. While there are legitimate uses for this capability, using it in practice is relatively rare. However, it can happen unintentionally when adjusting cell borders with the mouse. Accommodate this case and generate accurate `.text` and `.metadata.text_as_html` for these tables.
* **Remedy macOS test failure not triggered by CI.** Generalize temp-file detection beyond hard-coded Linux-specific prefix.
* **Remove unnecessary warning log for using default layout model.**
* **Add chunking to partition_tsv** Even though partition_tsv() produces a single Table element, chunking is made available because the Table element is often larger than the desired chunk size and must be divided into smaller chunks.

## 0.13.6

### Enhancements

### Features

### Fixes

- **ValueError: Invalid file (FileType.UNK) when parsing Content-Type header with charset directive** URL response Content-Type headers are now parsed according to RFC 9110.

## 0.13.5

### Enhancements

### Features

### Fixes

* **KeyError raised when updating parent_id** In the past, combining `ListItem` elements could result in reusing the same memory location which then led to unexpected side effects when updating element IDs.
* **Bump unstructured-inference==0.7.29**: table transformer predictions are now removed if confidence is below threshold

## 0.13.4

### Enhancements

* **Unique and deterministic hash IDs for elements** Element IDs produced by any partitioning
  function are now deterministic and unique at the document level by default. Before, hashes were
  based only on text; however, they now also take into account the element's sequence number on a
  page, the page's number in the document, and the document's file name.
* **Enable remote chunking via unstructured-ingest** Chunking using unstructured-ingest was
  previously limited to local chunking using the strategies `basic` and `by_title`. Remote chunking
  options via the API are now accessible.
* **Save table in cells format**. `UnstructuredTableTransformerModel` is able to return predicted table in cells format

### Features

* **Add a `PDF_ANNOTATION_THRESHOLD` environment variable to control the capture of embedded links in `partition_pdf()` for `fast` strategy**.
* **Add integration with the Google Cloud Vision API**. Adds a third OCR provider, alongside Tesseract and Paddle: the Google Cloud Vision API.

### Fixes

* **Remove ElementMetadata.section field.**. This field was unused, not populated by any partitioners.

## 0.13.3

### Enhancements

* **Remove duplicate image elements**. Remove image elements identified by PDFMiner that have similar bounding boxes and the same text.
* **Add support for `start_index` in `html` links extraction**
* **Add `strategy` arg value to `_PptxPartitionerOptions`.** This makes this paritioning option available for sub-partitioners to come that may optionally use inference or other expensive operations to improve the partitioning.
* **Support pluggable sub-partitioner for PPTX Picture shapes.** Use a distinct sub-partitioner for partitioning PPTX Picture (image) shapes and allow the default picture sub-partitioner to be replaced at run-time by one of the user's choosing.
* **Introduce `starting_page_number` parameter to partitioning functions** It applies to those partitioners which support `page_number` in element's metadata: PDF, TIFF, XLSX, DOC, DOCX, PPT, PPTX.
* **Redesign the internal mechanism of assigning element IDs** This allows for further enhancements related to element IDs such as deterministic and document-unique hashes. The way partitioning functions operate hasn't changed, which means `unique_element_ids` continues to be `False` by default, utilizing text hashes.

### Features

### Fixes

* **Add support for extracting text from tag tails in HTML**. This fix adds ability to generate separate elements using tag tails.
* **Add support for extracting text from `<b>` tags in HTML** Now `partition_html()` can extract text from `<b>` tags inside container tags (like `<div>`, `<pre>`).
* **Fix pip-compile make target** Missing base.in dependency missing from requirments make file added

## 0.13.2

### Enhancements

### Features

### Fixes

* **Brings back missing word list files** that caused `partition` failures in 0.13.1.

## 0.13.1

### Enhancements

* **Drop constraint on pydantic, supporting later versions** All dependencies has pydantic pinned at an old version. This explicit pin was removed, allowing the latest version to be pulled in when requirements are compiled.

### Features

* **Add a set of new `ElementType`s to extend future element types**

### Fixes

* **Fix `partition_html()` swallowing some paragraphs**. The `partition_html()` only considers elements with limited depth to avoid becoming the text representation of a giant div. This fix increases the limit value.
* **Fix SFTP** Adds flag options to SFTP connector on whether to use ssh keys / agent, with flag values defaulting to False. This is to prevent looking for ssh files when using username and password. Currently, username and password are required, making that always the case.

## 0.13.0

### Enhancements

* **Add `.metadata.is_continuation` to text-split chunks.** `.metadata.is_continuation=True` is added to second-and-later chunks formed by text-splitting an oversized `Table` element but not to their counterpart `Text` element splits. Add this indicator for `CompositeElement` to allow text-split continuation chunks to be identified for downstream processes that may wish to skip intentionally redundant metadata values in continuation chunks.
* **Add `compound_structure_acc` metric to table eval.** Add a new property to `unstructured.metrics.table_eval.TableEvaluation`: `composite_structure_acc`, which is computed from the element level row and column index and content accuracy scores
* **Add `.metadata.orig_elements` to chunks.** `.metadata.orig_elements: list[Element]` is added to chunks during the chunking process (when requested) to allow access to information from the elements each chunk was formed from. This is useful for example to recover metadata fields that cannot be consolidated to a single value for a chunk, like `page_number`, `coordinates`, and `image_base64`.
* **Add `--include_orig_elements` option to Ingest CLI.** By default, when chunking, the original elements used to form each chunk are added to `chunk.metadata.orig_elements` for each chunk. * The `include_orig_elements` parameter allows the user to turn off this behavior to produce a smaller payload when they don't need this metadata.
* **Add Google VertexAI embedder** Adds VertexAI embeddings to support embedding via Google Vertex AI.

### Features

* **Chunking populates `.metadata.orig_elements` for each chunk.** This behavior allows the text and metadata of the elements combined to make each chunk to be accessed. This can be important for example to recover metadata such as `.coordinates` that cannot be consolidated across elements and so is dropped from chunks. This option is controlled by the `include_orig_elements` parameter to `partition_*()` or to the chunking functions. This option defaults to `True` so original-elements are preserved by default. This behavior is not yet supported via the REST APIs or SDKs but will be in a closely subsequent PR to other `unstructured` repositories. The original elements will also not serialize or deserialize yet; this will also be added in a closely subsequent PR.
* **Add Clarifai destination connector** Adds support for writing partitioned and chunked documents into Clarifai.

### Fixes

* **Fix `clean_pdfminer_inner_elements()` to remove only pdfminer (embedded) elements merged with inferred elements**. Previously, some embedded elements were removed even if they were not merged with inferred elements. Now, only embedded elements that are already merged with inferred elements are removed.
* **Clarify IAM Role Requirement for GCS Platform Connectors**. The GCS Source Connector requires Storage Object Viewer and GCS Destination Connector requires Storage Object Creator IAM roles.
* **Change table extraction defaults** Change table extraction defaults in favor of using `skip_infer_table_types` parameter and reflect these changes in documentation.
* **Fix OneDrive dates with inconsistent formatting** Adds logic to conditionally support dates returned by office365 that may vary in date formatting or may be a datetime rather than a string. See previous fix for SharePoint
* **Adds tracking for AstraDB** Adds tracking info so AstraDB can see what source called their api.
* **Support AWS Bedrock Embeddings in ingest CLI** The configs required to instantiate the bedrock embedding class are now exposed in the api and the version of boto being used meets the minimum requirement to introduce the bedrock runtime required to hit the service.
* **Change MongoDB redacting** Original redact secrets solution is causing issues in platform. This fix uses our standard logging redact solution.

## 0.12.6

### Enhancements

* **Improve ability to capture embedded links in `partition_pdf()` for `fast` strategy** Previously, a threshold value that affects the capture of embedded links was set to a fixed value by default. This allows users to specify the threshold value for better capturing.
* **Refactor `add_chunking_strategy` decorator to dispatch by name.** Add `chunk()` function to be used by the `add_chunking_strategy` decorator to dispatch chunking call based on a chunking-strategy name (that can be dynamic at runtime). This decouples chunking dispatch from only those chunkers known at "compile" time and enables runtime registration of custom chunkers.
* **Redefine `table_level_acc` metric for table evaluation.** `table_level_acc` now is an average of individual predicted table's accuracy. A predicted table's accuracy is defined as the sequence matching ratio between itself and its corresponding ground truth table.

### Features

* **Added Unstructured Platform Documentation** The Unstructured Platform is currently in beta. The documentation provides how-to guides for setting up workflow automation, job scheduling, and configuring source and destination connectors.

### Fixes

* **Partitioning raises on file-like object with `.name` not a local file path.** When partitioning a file using the `file=` argument, and `file` is a file-like object (e.g. io.BytesIO) having a `.name` attribute, and the value of `file.name` is not a valid path to a file present on the local filesystem, `FileNotFoundError` is raised. This prevents use of the `file.name` attribute for downstream purposes to, for example, describe the source of a document retrieved from a network location via HTTP.
* **Fix SharePoint dates with inconsistent formatting** Adds logic to conditionally support dates returned by office365 that may vary in date formatting or may be a datetime rather than a string.
* **Include warnings** about the potential risk of installing a version of `pandoc` which does not support RTF files + instructions that will help resolve that issue.
* **Incorporate the `install-pandoc` Makefile recipe** into relevant stages of CI workflow, ensuring it is a version that supports RTF input files.
* **Fix Google Drive source key** Allow passing string for source connector key.
* **Fix table structure evaluations calculations** Replaced special value `-1.0` with `np.nan` and corrected rows filtering of files metrics basing on that.
* **Fix Sharepoint-with-permissions test** Ignore permissions metadata, update test.
* **Fix table structure evaluations for edge case** Fixes the issue when the prediction does not contain any table - no longer errors in such case.

## 0.12.5

### Enhancements

### Features

* Add `date_from_file_object` parameter to partition. If True and if file is provided via `file` parameter it will cause partition to infer last modified date from `file`'s content. If False, last modified metadata will be `None`.
* **Header and footer detection for fast strategy** `partition_pdf` with `fast` strategy now
  detects elements that are in the top or bottom 5 percent of the page as headers and footers.
* **Add parent_element to overlapping case output** Adds parent_element to the output for `identify_overlapping_or_nesting_case` and `catch_overlapping_and_nested_bboxes` functions.
* **Add table structure evaluation** Adds a new function to evaluate the structure of a table and return a metric that represents the quality of the table structure. This function is used to evaluate the quality of the table structure and the table contents.
* **Add AstraDB destination connector** Adds support for writing embedded documents into an AstraDB vector database.
* **Add OctoAI embedder** Adds support for embeddings via OctoAI.

### Fixes

* **Fix passing list type parameters when calling unstructured API via `partition_via_api()`** Update `partition_via_api()` to convert all list type parameters to JSON formatted strings before calling the unstructured client SDK. This will support image block extraction via `partition_via_api()`.
* **Fix `check_connection` in opensearch, databricks, postgres, azure connectors**
* **Fix don't treat plain text files with double quotes as JSON** If a file can be deserialized as JSON but it deserializes as a string, treat it as plain text even though it's valid JSON.
* **Fix `check_connection` in opensearch, databricks, postgres, azure connectors**
* **Fix cluster of bugs in `partition_xlsx()` that dropped content.** Algorithm for detecting "subtables" within a worksheet dropped table elements for certain patterns of populated cells such as when a trailing single-cell row appeared in a contiguous block of populated cells.
* **Improved documentation**. Fixed broken links and improved readability on `Key Concepts` page.
* **Rename `OpenAiEmbeddingConfig` to `OpenAIEmbeddingConfig`.**
* **Fix partition_json() doesn't chunk.** The `@add_chunking_strategy` decorator was missing from `partition_json()` such that pre-partitioned documents serialized to JSON did not chunk when a chunking-strategy was specified.

## 0.12.4

### Enhancements

* **Apply New Version of `black` formatting** The `black` library recently introduced a new major version that introduces new formatting conventions. This change brings code in the `unstructured` repo into compliance with the new conventions.
* **Move ingest imports to local scopes** Moved ingest dependencies into local scopes to be able to import ingest connector classes without the need of installing imported external dependencies. This allows lightweight use of the classes (not the instances. to use the instances as intended you'll still need the dependencies).
* **Add support for `.p7s` files** `partition_email` can now process `.p7s` files. The signature for the signed message is extracted and added to metadata.
* **Fallback to valid content types for emails** If the user selected content type does not exist on the email message, `partition_email` now falls back to anoter valid content type if it's available.

### Features

* **Add .heic file partitioning** .heic image files were previously unsupported and are now supported though partition_image()
* **Add the ability to specify an alternate OCR** implementation by implementing an `OCRAgent` interface and specify it using `OCR_AGENT` environment variable.
* **Add Vectara destination connector** Adds support for writing partitioned documents into a Vectara index.
* **Add ability to detect text in .docx inline shapes** extensions of docx partition, extracts text from inline shapes and includes them in paragraph's text

### Fixes

* **Fix `partition_pdf()` not working when using chipper model with `file`**
* **Handle common incorrect arguments for `languages` and `ocr_languages`** Users are regularly receiving errors on the API because they are defining `ocr_languages` or `languages` with additional quotationmarks, brackets, and similar mistakes. This update handles common incorrect arguments and raises an appropriate warning.
* **Default `hi_res_model_name` now relies on `unstructured-inference`** When no explicit `hi_res_model_name` is passed into `partition` or `partition_pdf_or_image` the default model is picked by `unstructured-inference`'s settings or os env variable `UNSTRUCTURED_HI_RES_MODEL_NAME`; it now returns the same model name regardless of `infer_table_structure`'s value; this function will be deprecated in the future and the default model name will simply rely on `unstructured-inference` and will not consider os env in a future release.
* **Fix remove Vectara requirements from setup.py - there are no dependencies**
* **Add missing dependency files to package manifest**. Updates the file path for the ingest
  dependencies and adds missing extra dependencies.
* **Fix remove Vectara requirements from setup.py - there are no dependencies **
* **Add title to Vectara upload - was not separated out from initial connector **
* **Fix change OpenSearch port to fix potential conflict with Elasticsearch in ingest test **

## 0.12.3

### Enhancements

* **Driver for MongoDB connector.** Adds a driver with `unstructured` version information to the
  MongoDB connector.

### Features

* **Add Databricks Volumes destination connector** Databricks Volumes connector added to ingest CLI.  Users may now use `unstructured-ingest` to write partitioned data to a Databricks Volumes storage service.

### Fixes

* **Fix support for different Chipper versions and prevent running PDFMiner with Chipper**
* **Treat YAML files as text.** Adds YAML MIME types to the file detection code and treats those
  files as text.
* **Fix FSSpec destination connectors check_connection.** FSSpec destination connectors did not use `check_connection`. There was an error when trying to `ls` destination directory - it may not exist at the moment of connector creation. Now `check_connection` calls `ls` on bucket root and this method is called on `initialize` of destination connector.
* **Fix databricks-volumes extra location.** `setup.py` is currently pointing to the wrong location for the databricks-volumes extra requirements. This results in errors when trying to build the wheel for unstructured. This change updates to point to the correct path.
* **Fix uploading None values to Chroma and Pinecone.** Removes keys with None values with Pinecone and Chroma destinations. Pins Pinecone dependency
* **Update documentation.** (i) best practice for table extration by using 'skip_infer_table_types' param, instead of 'pdf_infer_table_structure', and (ii) fixed CSS, RST issues and typo in the documentation.
* **Fix postgres storage of link_texts.** Formatting of link_texts was breaking metadata storage.

## 0.12.2

### Enhancements

### Features

### Fixes

* **Fix index error in table processing.** Bumps the `unstructured-inference` version to address and
  index error that occurs on some tables in the table transformer object.

## 0.12.1

### Enhancements

* **Allow setting image block crop padding parameter** In certain circumstances, adjusting the image block crop padding can improve image block extraction by preventing extracted image blocks from being clipped.
* **Add suport for bitmap images in `partition_image`** Adds support for `.bmp` files in
  `partition`, `partition_image`, and `detect_filetype`.
* **Keep all image elements when using "hi_res" strategy** Previously, `Image` elements with small chunks of text were ignored unless the image block extraction parameters (`extract_images_in_pdf` or `extract_image_block_types`) were specified. Now, all image elements are kept regardless of whether the image block extraction parameters are specified.
* **Add filetype detection for `.wav` files.** Add filetpye detection for `.wav` files.
* **Add "basic" chunking strategy.** Add baseline chunking strategy that includes all shared chunking behaviors without breaking chunks on section or page boundaries.
* **Add overlap option for chunking.** Add option to overlap chunks. Intra-chunk and inter-chunk overlap are requested separately. Intra-chunk overlap is applied only to the second and later chunks formed by text-splitting an oversized chunk. Inter-chunk overlap may also be specified; this applies overlap between "normal" (not-oversized) chunks.
* **Salesforce connector accepts private key path or value.** Salesforce parameter `private-key-file` has been renamed to `private-key`. Private key can be provided as path to file or file contents.
* **Update documentation**: (i) added verbiage about the free API cap limit, (ii) added deprecation warning on ``Staging`` bricks in favor of ``Destination Connectors``, (iii) added warning and code examples to use the SaaS API Endpoints using CLI-vs-SDKs, (iv) fixed example pages formatting, (v) added deprecation on ``model_name`` in favor of ``hi_res_model_name``, (vi) added ``extract_images_in_pdf`` usage in ``partition_pdf`` section, (vii) reorganize and improve the documentation introduction section, and (viii) added PDF table extraction best practices.
* **Add "basic" chunking to ingest CLI.** Add options to ingest CLI allowing access to the new "basic" chunking strategy and overlap options.
* **Make Elasticsearch Destination connector arguments optional.** Elasticsearch Destination connector write settings are made optional and will rely on default values when not specified.
* **Normalize Salesforce artifact names.** Introduced file naming pattern present in other connectors to Salesforce connector.
* **Install Kapa AI chatbot.** Added Kapa.ai website widget on the documentation.

### Features

* **MongoDB Source Connector.** New source connector added to all CLI ingest commands to support downloading/partitioning files from MongoDB.
* **Add OpenSearch source and destination connectors.** OpenSearch, a fork of Elasticsearch, is a popular storage solution for various functionality such as search, or providing intermediary caches within data pipelines. Feature: Added OpenSearch source connector to support downloading/partitioning files. Added OpenSearch destination connector to be able to ingest documents from any supported source, embed them and write the embeddings / documents into OpenSearch.

### Fixes

* **Fix GCS connector converting JSON to string with single quotes.** FSSpec serialization caused conversion of JSON token to string with single quotes. GCS requires token in form of dict so this format is now assured.
* **Pin version of unstructured-client** Set minimum version of unstructured-client to avoid raising a TypeError when passing `api_key_auth` to `UnstructuredClient`
* **Fix the serialization of the Pinecone destination connector.** Presence of the PineconeIndex object breaks serialization due to TypeError: cannot pickle '_thread.lock' object. This removes that object before serialization.
* **Fix the serialization of the Elasticsearch destination connector.** Presence of the _client object breaks serialization due to TypeError: cannot pickle '_thread.lock' object. This removes that object before serialization.
* **Fix the serialization of the Postgres destination connector.** Presence of the _client object breaks serialization due to TypeError: cannot pickle '_thread.lock' object. This removes that object before serialization.
* **Fix documentation and sample code for Chroma.** Was pointing to wrong examples..
* **Fix flatten_dict to be able to flatten tuples inside dicts** Update flatten_dict function to support flattening tuples inside dicts. This is necessary for objects like Coordinates, when the object is not written to the disk, therefore not being converted to a list before getting flattened (still being a tuple).
* **Fix the serialization of the Chroma destination connector.** Presence of the ChromaCollection object breaks serialization due to TypeError: cannot pickle 'module' object. This removes that object before serialization.
* **Fix fsspec connectors returning version as integer.** Connector data source versions should always be string values, however we were using the integer checksum value for the version for fsspec connectors. This casts that value to a string.

## 0.12.0

### Enhancements

* **Drop support for python3.8** All dependencies are now built off of the minimum version of python being `3.10`

## 0.11.9

### Enhancements

* **Rename kwargs related to extracting image blocks** Rename the kwargs related to extracting image blocks for consistency and API usage.

### Features

* **Add PostgreSQL/SQLite destination connector** PostgreSQL and SQLite connector added to ingest CLI.  Users may now use `unstructured-ingest` to write partitioned data to a PostgreSQL or SQLite database. And write embeddings to PostgreSQL pgvector database.

### Fixes

* **Handle users providing fully spelled out languages** Occasionally some users are defining the `languages` param as a fully spelled out language instead of a language code. This adds a dictionary for common languages so those small mistakes are caught and silently fixed.
* **Fix unequal row-length in HTMLTable.text_as_html.** Fixes to other aspects of partition_html() in v0.11 allowed unequal cell-counts in table rows. Make the cells in each row correspond 1:1 with cells in the original table row. This fix also removes "noise" cells resulting from HTML-formatting whitespace and eliminates the "column-shifting" of cells that previously resulted from noise-cells.
* **Fix MongoDB connector URI password redaction.** MongoDB documentation states that characters `$ : / ? # [ ] @` must be percent encoded. URIs with password containing such special character were not redacted.

## 0.11.8

### Enhancements

* **Add SaaS API User Guide.** This documentation serves as a guide for Unstructured SaaS API users to register, receive an API key and URL, and manage your account and billing information.
* **Add inter-chunk overlap capability.** Implement overlap between chunks. This applies to all chunks prior to any text-splitting of oversized chunks so is a distinct behavior; overlap at text-splits of oversized chunks is independent of inter-chunk overlap (distinct chunk boundaries) and can be requested separately. Note this capability is not yet available from the API but will shortly be made accessible using a new `overlap_all` kwarg on partition functions.

### Features

### Fixes

## 0.11.7

### Enhancements

* **Add intra-chunk overlap capability.** Implement overlap for split-chunks where text-splitting is used to divide an oversized chunk into two or more chunks that fit in the chunking window. Note this capability is not yet available from the API but will shortly be made accessible using a new `overlap` kwarg on partition functions.
* **Update encoders to leverage dataclasses** All encoders now follow a class approach which get annotated with the dataclass decorator. Similar to the connectors, it uses a nested dataclass for the configs required to configure a client as well as a field/property approach to cache the client. This makes sure any variable associated with the class exists as a dataclass field.

### Features

* **Add Qdrant destination connector.** Adds support for writing documents and embeddings into a Qdrant collection.
* **Store base64 encoded image data in metadata fields.** Rather than saving to file, stores base64 encoded data of the image bytes and the mimetype for the image in metadata fields: `image_base64` and `image_mime_type` (if that is what the user specifies by some other param like `pdf_extract_to_payload`). This would allow the API to have parity with the library.

### Fixes

* **Fix table structure metric script** Update the call to table agent to now provide OCR tokens as required
* **Fix element extraction not working when using "auto" strategy for pdf and image** If element extraction is specified, the "auto" strategy falls back to the "hi_res" strategy.
* **Fix a bug passing a custom url to `partition_via_api`** Users that self host the api were not able to pass their custom url to `partition_via_api`.

## 0.11.6

### Enhancements

* **Update the layout analysis script.** The previous script only supported annotating `final` elements. The updated script also supports annotating `inferred` and `extracted` elements.
* **AWS Marketplace API documentation**: Added the user guide, including setting up VPC and CloudFormation, to deploy Unstructured API on AWS platform.
* **Azure Marketplace API documentation**: Improved the user guide to deploy Azure Marketplace API by adding references to Azure documentation.
* **Integration documentation**: Updated URLs for the `staging_for` bricks

### Features

* **Partition emails with base64-encoded text.** Automatically handles and decodes base64 encoded text in emails with content type `text/plain` and `text/html`.
* **Add Chroma destination connector** Chroma database connector added to ingest CLI.  Users may now use `unstructured-ingest` to write partitioned/embedded data to a Chroma vector database.
* **Add Elasticsearch destination connector.** Problem: After ingesting data from a source, users might want to move their data into a destination. Elasticsearch is a popular storage solution for various functionality such as search, or providing intermediary caches within data pipelines. Feature: Added Elasticsearch destination connector to be able to ingest documents from any supported source, embed them and write the embeddings / documents into Elasticsearch.

### Fixes

* **Enable --fields argument omission for elasticsearch connector** Solves two bugs where removing the optional parameter --fields broke the connector due to an integer processing error and using an elasticsearch config for a destination connector resulted in a serialization issue when optional parameter --fields was not provided.
* **Add hi_res_model_name** Adds kwarg to relevant functions and add comments that model_name is to be deprecated.

## 0.11.5

### Enhancements

### Features

### Fixes

* **Fix `partition_pdf()` and `partition_image()` importation issue.** Reorganize `pdf.py` and `image.py` modules to be consistent with other types of document import code.

## 0.11.4

### Enhancements

* **Refactor image extraction code.** The image extraction code is moved from `unstructured-inference` to `unstructured`.
* **Refactor pdfminer code.** The pdfminer code is moved from `unstructured-inference` to `unstructured`.
* **Improve handling of auth data for fsspec connectors.** Leverage an extension of the dataclass paradigm to support a `sensitive` annotation for fields related to auth (i.e. passwords, tokens). Refactor all fsspec connectors to use explicit access configs rather than a generic dictionary.
* **Add glob support for fsspec connectors** Similar to the glob support in the ingest local source connector, similar filters are now enabled on all fsspec based source connectors to limit files being partitioned.
* Define a constant for the splitter "+" used in tesseract ocr languages.

### Features

* **Save tables in PDF's separately as images.** The "table" elements are saved as `table-<pageN>-<tableN>.jpg`. This filename is presented in the `image_path` metadata field for the Table element. The default would be to not do this.
* **Add Weaviate destination connector** Weaviate connector added to ingest CLI.  Users may now use `unstructured-ingest` to write partitioned data from over 20 data sources (so far) to a Weaviate object collection.
* **Sftp Source Connector.** New source connector added to support downloading/partitioning files from Sftp.

### Fixes

* **Fix pdf `hi_res` partitioning failure when pdfminer fails.** Implemented logic to fall back to the "inferred_layout + OCR" if pdfminer fails in the `hi_res` strategy.
* **Fix a bug where image can be scaled too large for tesseract** Adds a limit to prevent auto-scaling an image beyond the maximum size `tesseract` can handle for ocr layout detection
* **Update partition_csv to handle different delimiters** CSV files containing both non-comma delimiters and commas in the data were throwing an error in Pandas. `partition_csv` now identifies the correct delimiter before the file is processed.
* **partition returning cid code in `hi_res`** occasionally pdfminer can fail to decode the text in an pdf file and return cid code as text. Now when this happens the text from OCR is used.

## 0.11.2

### Enhancements

* **Updated Documentation**: (i) Added examples, and (ii) API Documentation, including Usage, SDKs, Azure Marketplace, and parameters and validation errors.

### Features

* * **Add Pinecone destination connector.** Problem: After ingesting data from a source, users might want to produce embeddings for their data and write these into a vector DB. Pinecone is an option among these vector databases. Feature: Added Pinecone destination connector to be able to ingest documents from any supported source, embed them and write the embeddings / documents into Pinecone.

### Fixes

* **Process chunking parameter names in ingest correctly** Solves a bug where chunking parameters weren't being processed and used by ingest cli by renaming faulty parameter names and prepends; adds relevant parameters to ingest pinecone test to verify that the parameters are functional.

## 0.11.1

### Enhancements

* **Use `pikepdf` to repair invalid PDF structure** for PDFminer when we see error `PSSyntaxError` when PDFminer opens the document and creates the PDFminer pages object or processes a single PDF page.
* **Batch Source Connector support** For instances where it is more optimal to read content from a source connector in batches, a new batch ingest doc is added which created multiple ingest docs after reading them in in batches per process.

### Features

* **Staging Brick for Coco Format** Staging brick which converts a list of Elements into Coco Format.
* **Adds HubSpot connector** Adds connector to retrieve call, communications, emails, notes, products and tickets from HubSpot

### Fixes

* **Do not extract text of `<style>` tags in HTML.** `<style>` tags containing CSS in invalid positions previously contributed to element text. Do not consider text node of a `<style>` element as textual content.
* **Fix DOCX merged table cell repeats cell text.** Only include text for a merged cell, not for each underlying cell spanned by the merge.
* **Fix tables not extracted from DOCX header/footers.** Headers and footers in DOCX documents skip tables defined in the header and commonly used for layout/alignment purposes. Extract text from tables as a string and include in the `Header` and `Footer` document elements.
* **Fix output filepath for fsspec-based source connectors.** Previously the base directory was being included in the output filepath unnecessarily.

## 0.11.0

### Enhancements

* **Add a class for the strategy constants.** Add a class `PartitionStrategy` for the strategy constants and use the constants to replace strategy strings.
* **Temporary Support for paddle language parameter.** User can specify default langage code for paddle with ENV `DEFAULT_PADDLE_LANG` before we have the language mapping for paddle.
* **Improve DOCX page-break fidelity.** Improve page-break fidelity such that a paragraph containing a page-break is split into two elements, one containing the text before the page-break and the other the text after. Emit the PageBreak element between these two and assign the correct page-number (n and n+1 respectively) to the two textual elements.

### Features

* **Add ad-hoc fields to `ElementMetadata` instance.** End-users can now add their own metadata fields simply by assigning to an element-metadata attribute-name of their choice, like `element.metadata.coefficient = 0.58`. These fields will round-trip through JSON and can be accessed with dotted notation.
* **MongoDB Destination Connector.** New destination connector added to all CLI ingest commands to support writing partitioned json output to mongodb.

### Fixes

* **Fix `TYPE_TO_TEXT_ELEMENT_MAP`.** Updated `Figure` mapping from `FigureCaption` to `Image`.
* **Handle errors when extracting PDF text** Certain pdfs throw unexpected errors when being opened by `pdfminer`, causing `partition_pdf()` to fail. We expect to be able to partition smoothly using an alternative strategy if text extraction doesn't work.  Added exception handling to handle unexpected errors when extracting pdf text and to help determine pdf strategy.
* **Fix `fast` strategy fall back to `ocr_only`** The `fast` strategy should not fall back to a more expensive strategy.
* **Remove default user ./ssh folder** The default notebook user during image build would create the known_hosts file with incorrect ownership, this is legacy and no longer needed so it was removed.
* **Include `languages` in metadata when partitioning `strategy=hi_res` or `fast`** User defined `languages` was previously used for text detection, but not included in the resulting element metadata for some strategies. `languages` will now be included in the metadata regardless of partition strategy for pdfs and images.
* **Handle a case where Paddle returns a list item in ocr_data as None** In partition, while parsing PaddleOCR data, it was assumed that PaddleOCR does not return None for any list item in ocr_data. Removed the assumption by skipping the text region whenever this happens.
* **Fix some pdfs returning `KeyError: 'N'`** Certain pdfs were throwing this error when being opened by pdfminer. Added a wrapper function for pdfminer that allows these documents to be partitioned.
* **Fix mis-splits on `Table` chunks.** Remedies repeated appearance of full `.text_as_html` on metadata of each `TableChunk` split from a `Table` element too large to fit in the chunking window.
* **Import tables_agent from inference** so that we don't have to initialize a global table agent in unstructured OCR again
* **Fix empty table is identified as bulleted-table.** A table with no text content was mistakenly identified as a bulleted-table and processed by the wrong branch of the initial HTML partitioner.
* **Fix partition_html() emits empty (no text) tables.** A table with cells nested below a `<thead>` or `<tfoot>` element was emitted as a table element having no text and unparseable HTML in `element.metadata.text_as_html`. Do not emit empty tables to the element stream.
* **Fix HTML `element.metadata.text_as_html` contains spurious `<br>` elements in invalid locations.** The HTML generated for the `text_as_html` metadata for HTML tables contained `<br>` elements invalid locations like between `<table>` and `<tr>`. Change the HTML generator such that these do not appear.
* **Fix HTML table cells enclosed in `<thead>` and `<tfoot>` elements are dropped.** HTML table cells nested in a `<thead>` or `<tfoot>` element were not detected and the text in those cells was omitted from the table element text and `.text_as_html`. Detect table rows regardless of the semantic tag they may be nested in.
* **Remove whitespace padding from `.text_as_html`.** `tabulate` inserts padding spaces to achieve visual alignment of columns in HTML tables it generates. Add our own HTML generator to do this simple job and omit that padding as well as newlines ("\n") used for human readability.
* **Fix local connector with absolute input path** When passed an absolute filepath for the input document path, the local connector incorrectly writes the output file to the input file directory. This fixes such that the output in this case is written to `output-dir/input-filename.json`

## 0.10.30

### Enhancements

* **Support nested DOCX tables.** In DOCX, like HTML, a table cell can itself contain a table. In this case, create nested HTML tables to reflect that structure and create a plain-text table with captures all the text in nested tables, formatting it as a reasonable facsimile of a table.
* **Add connection check to ingest connectors** Each source and destination connector now support a `check_connection()` method which makes sure a valid connection can be established with the source/destination given any authentication credentials in a lightweight request.

### Features

* **Add functionality to do a second OCR on cropped table images.** Changes to the values for scaling ENVs affect entire page OCR output(OCR regression) so we now do a second OCR for tables.
* **Adds ability to pass timeout for a request when partitioning via a `url`.** `partition` now accepts a new optional parameter `request_timeout` which if set will prevent any `requests.get` from hanging indefinitely and instead will raise a timeout error. This is useful when partitioning a url that may be slow to respond or may not respond at all.

### Fixes

* **Fix logic that determines pdf auto strategy.** Previously, `_determine_pdf_auto_strategy` returned `hi_res` strategy only if `infer_table_structure` was true. It now returns the `hi_res` strategy if either `infer_table_structure` or `extract_images_in_pdf` is true.
* **Fix invalid coordinates when parsing tesseract ocr data.** Previously, when parsing tesseract ocr data, the ocr data had invalid bboxes if zoom was set to `0`. A logical check is now added to avoid such error.
* **Fix ingest partition parameters not being passed to the api.** When using the --partition-by-api flag via unstructured-ingest, none of the partition arguments are forwarded, meaning that these options are disregarded. With this change, we now pass through all of the relevant partition arguments to the api. This allows a user to specify all of the same partition arguments they would locally and have them respected when specifying --partition-by-api.
* **Support tables in section-less DOCX.** Generalize solution for MS Chat Transcripts exported as DOCX by including tables in the partitioned output when present.
* **Support tables that contain only numbers when partitioning via `ocr_only`** Tables that contain only numbers are returned as floats in a pandas.DataFrame when the image is converted from `.image_to_data()`. An AttributeError was raised downstream when trying to `.strip()` the floats.
* **Improve DOCX page-break detection.** DOCX page breaks are reliably indicated by `w:lastRenderedPageBreak` elements present in the document XML. Page breaks are NOT reliably indicated by "hard" page-breaks inserted by the author and when present are redundant to a `w:lastRenderedPageBreak` element so cause over-counting if used. Use rendered page-breaks only.

## 0.10.29

### Enhancements

* **Adds include_header argument for partition_csv and partition_tsv** Now supports retaining header rows in CSV and TSV documents element partitioning.
* **Add retry logic for all source connectors** All http calls being made by the ingest source connectors have been isolated and wrapped by the `SourceConnectionNetworkError` custom error, which triggers the retry logic, if enabled, in the ingest pipeline.
* **Google Drive source connector supports credentials from memory** Originally, the connector expected a filepath to pull the credentials from when creating the client. This was expanded to support passing that information from memory as a dict if access to the file system might not be available.
* **Add support for generic partition configs in ingest cli** Along with the explicit partition options supported by the cli, an `additional_partition_args` arg was added to allow users to pass in any other arguments that should be added when calling partition(). This helps keep any changes to the input parameters of the partition() exposed in the CLI.
* **Map full output schema for table-based destination connectors** A full schema was introduced to map the type of all output content from the json partition output and mapped to a flattened table structure to leverage table-based destination connectors. The delta table destination connector was updated at the moment to take advantage of this.
* **Incorporate multiple embedding model options into ingest, add diff test embeddings** Problem: Ingest pipeline already supported embedding functionality, however users might want to use different types of embedding providers. Enhancement: Extend ingest pipeline so that users can specify and embed via a particular embedding provider from a range of options. Also adds a diff test to compare output from an embedding module with the expected output

### Features

* **Allow setting table crop parameter** In certain circumstances, adjusting the table crop padding may improve table.

### Fixes

* **Fixes `partition_text` to prevent empty elements** Adds a check to filter out empty bullets.
* **Handle empty string for `ocr_languages` with values for `languages`** Some API users ran into an issue with sending `languages` params because the API defaulted to also using an empty string for `ocr_languages`. This update handles situations where `languages` is defined and `ocr_languages` is an empty string.
* **Fix PDF tried to loop through None** Previously the PDF annotation extraction tried to loop through `annots` that resolved out as None. A logical check added to avoid such error.
* **Ingest session handler not being shared correctly** All ingest docs that leverage the session handler should only need to set it once per process. It was recreating it each time because the right values weren't being set nor available given how dataclasses work in python.
* **Ingest download-only fix.** Previously the download only flag was being checked after the doc factory pipeline step, which occurs before the files are actually downloaded by the source node. This check was moved after the source node to allow for the files to be downloaded first before exiting the pipeline.
* **Fix flaky chunk-metadata.** Prior implementation was sensitive to element order in the section resulting in metadata values sometimes being dropped. Also, not all metadata items can be consolidated across multiple elements (e.g. coordinates) and so are now dropped from consolidated metadata.
* **Fix tesseract error `Estimating resolution as X`** leaded by invalid language parameters input. Proceed with defalut language `eng` when `lang.py` fails to find valid language code for tesseract, so that we don't pass an empty string to tesseract CLI and raise an exception in downstream.

## 0.10.28

### Enhancements

* **Add table structure evaluation helpers** Adds functions to evaluate the similarity between predicted table structure and actual table structure.
* **Use `yolox` by default for table extraction when partitioning pdf/image** `yolox` model provides higher recall of the table regions than the quantized version and it is now the default element detection model when `infer_table_structure=True` for partitioning pdf/image files
* **Remove pdfminer elements from inside tables** Previously, when using `hi_res` some elements where extracted using pdfminer too, so we removed pdfminer from the tables pipeline to avoid duplicated elements.
* **Fsspec downstream connectors** New destination connector added to ingest CLI, users may now use `unstructured-ingest` to write to any of the following:
  * Azure
  * Box
  * Dropbox
  * Google Cloud Service

### Features

* **Update `ocr_only` strategy in `partition_pdf()`** Adds the functionality to get accurate coordinate data when partitioning PDFs and Images with the `ocr_only` strategy.

### Fixes

* **Fixed SharePoint permissions for the fetching to be opt-in** Problem: Sharepoint permissions were trying to be fetched even when no reletad cli params were provided, and this gave an error due to values for those keys not existing. Fix: Updated getting keys to be with .get() method and changed the "skip-check" to check individual cli params rather than checking the existance of a config object.
* **Fixes issue where tables from markdown documents were being treated as text** Problem: Tables from markdown documents were being treated as text, and not being extracted as tables. Solution: Enable the `tables` extension when instantiating the `python-markdown` object. Importance: This will allow users to extract structured data from tables in markdown documents.
* **Fix wrong logger for paddle info** Replace the logger from unstructured-inference with the logger from unstructured for paddle_ocr.py module.
* **Fix ingest pipeline to be able to use chunking and embedding together** Problem: When ingest pipeline was using chunking and embedding together, embedding outputs were empty and the outputs of chunking couldn't be re-read into memory and be forwarded to embeddings. Fix: Added CompositeElement type to TYPE_TO_TEXT_ELEMENT_MAP to be able to process CompositeElements with unstructured.staging.base.isd_to_elements
* **Fix unnecessary mid-text chunk-splitting.** The "pre-chunker" did not consider separator blank-line ("\n\n") length when grouping elements for a single chunk. As a result, sections were frequently over-populated producing a over-sized chunk that required mid-text splitting.
* **Fix frequent dissociation of title from chunk.** The sectioning algorithm included the title of the next section with the prior section whenever it would fit, frequently producing association of a section title with the prior section and dissociating it from its actual section. Fix this by performing combination of whole sections only.
* **Fix PDF attempt to get dict value from string.** Fixes a rare edge case that prevented some PDF's from being partitioned. The `get_uris_from_annots` function tried to access the dictionary value of a string instance variable. Assign `None` to the annotation variable if the instance type is not dictionary to avoid the erroneous attempt.

## 0.10.27

### Enhancements

* **Leverage dict to share content across ingest pipeline** To share the ingest doc content across steps in the ingest pipeline, this was updated to use a multiprocessing-safe dictionary so changes get persisted and each step has the option to modify the ingest docs in place.

### Features

### Fixes

* **Removed `ebooklib` as a dependency** `ebooklib` is licensed under AGPL3, which is incompatible with the Apache 2.0 license. Thus it is being removed.
* **Caching fixes in ingest pipeline** Previously, steps like the source node were not leveraging parameters such as `re_download` to dictate if files should be forced to redownload rather than use what might already exist locally.

## 0.10.26

### Enhancements

* **Add text CCT CI evaluation workflow** Adds cct text extraction evaluation metrics to the current ingest workflow to measure the performance of each file extracted as well as aggregated-level performance.

### Features

* **Functionality to catch and classify overlapping/nested elements** Method to identify overlapping-bboxes cases within detected elements in a document. It returns two values: a boolean defining if there are overlapping elements present, and a list reporting them with relevant metadata. The output includes information about the `overlapping_elements`, `overlapping_case`, `overlapping_percentage`, `largest_ngram_percentage`, `overlap_percentage_total`, `max_area`, `min_area`, and `total_area`.
* **Add Local connector source metadata** python's os module used to pull stats from local file when processing via the local connector and populates fields such as last modified time, created time.

### Fixes

* **Fixes elements partitioned from an image file missing certain metadata** Metadata for image files, like file type, was being handled differently from other file types. This caused a bug where other metadata, like the file name, was being missed. This change brought metadata handling for image files to be more in line with the handling for other file types so that file name and other metadata fields are being captured.
* **Adds `typing-extensions` as an explicit dependency** This package is an implicit dependency, but the module is being imported directly in `unstructured.documents.elements` so the dependency should be explicit in case changes in other dependencies lead to `typing-extensions` being dropped as a dependency.
* **Stop passing `extract_tables` to `unstructured-inference` since it is now supported in `unstructured` instead** Table extraction previously occurred in `unstructured-inference`, but that logic, except for the table model itself, is now a part of the `unstructured` library. Thus the parameter triggering table extraction is no longer passed to the `unstructured-inference` package. Also noted the table output regression for PDF files.
* **Fix a bug in Table partitioning** Previously the `skip_infer_table_types` variable used in `partition` was not being passed down to specific file partitioners. Now you can utilize the `skip_infer_table_types` list variable when calling `partition` to specify the filetypes for which you want to skip table extraction, or the `infer_table_structure` boolean variable on the file specific partitioning function.
* **Fix partition docx without sections** Some docx files, like those from teams output, do not contain sections and it would produce no results because the code assumes all components are in sections. Now if no sections is detected from a document we iterate through the paragraphs and return contents found in the paragraphs.
* **Fix out-of-order sequencing of split chunks.** Fixes behavior where "split" chunks were inserted at the beginning of the chunk sequence. This would produce a chunk sequence like [5a, 5b, 3a, 3b, 1, 2, 4] when sections 3 and 5 exceeded `max_characters`.
* **Deserialization of ingest docs fixed** When ingest docs are being deserialized as part of the ingest pipeline process (cli), there were certain fields that weren't getting persisted (metadata and date processed). The from_dict method was updated to take these into account and a unit test added to check.
* **Map source cli command configs when destination set** Due to how the source connector is dynamically called when the destination connector is set via the CLI, the configs were being set incorrectoy, causing the source connector to break. The configs were fixed and updated to take into account Fsspec-specific connectors.

## 0.10.25

### Enhancements

* **Duplicate CLI param check** Given that many of the options associated with the `Click` based cli ingest commands are added dynamically from a number of configs, a check was incorporated to make sure there were no duplicate entries to prevent new configs from overwriting already added options.
* **Ingest CLI refactor for better code reuse** Much of the ingest cli code can be templated and was a copy-paste across files, adding potential risk. Code was refactored to use a base class which had much of the shared code templated.

### Features

* **Table OCR refactor** support Table OCR with pre-computed OCR data to ensure we only do one OCR for entrie document. User can specify
  ocr agent tesseract/paddle in environment variable `OCR_AGENT` for OCRing the entire document.
* **Adds accuracy function** The accuracy scoring was originally an option under `calculate_edit_distance`. For easy function call, it is now a wrapper around the original function that calls edit_distance and return as "score".
* **Adds HuggingFaceEmbeddingEncoder** The HuggingFace Embedding Encoder uses a local embedding model as opposed to using an API.
* **Add AWS bedrock embedding connector** `unstructured.embed.bedrock` now provides a connector to use AWS bedrock's `titan-embed-text` model to generate embeddings for elements. This features requires valid AWS bedrock setup and an internet connectionto run.

### Fixes

* **Import PDFResourceManager more directly** We were importing `PDFResourceManager` from `pdfminer.converter` which was causing an error for some users. We changed to import from the actual location of `PDFResourceManager`, which is `pdfminer.pdfinterp`.
* **Fix language detection of elements with empty strings** This resolves a warning message that was raised by `langdetect` if the language was attempted to be detected on an empty string. Language detection is now skipped for empty strings.
* **Fix chunks breaking on regex-metadata matches.** Fixes "over-chunking" when `regex_metadata` was used, where every element that contained a regex-match would start a new chunk.
* **Fix regex-metadata match offsets not adjusted within chunk.** Fixes incorrect regex-metadata match start/stop offset in chunks where multiple elements are combined.
* **Map source cli command configs when destination set** Due to how the source connector is dynamically called when the destination connector is set via the CLI, the configs were being set incorrectoy, causing the source connector to break. The configs were fixed and updated to take into account Fsspec-specific connectors.
* **Fix metrics folder not discoverable** Fixes issue where unstructured/metrics folder is not discoverable on PyPI by adding an `__init__.py` file under the folder.
* **Fix a bug when `parition_pdf` get `model_name=None`** In API usage the `model_name` value is `None` and the `cast` function in `partition_pdf` would return `None` and lead to attribution error. Now we use `str` function to explicit convert the content to string so it is garanteed to have `starts_with` and other string functions as attributes
* **Fix html partition fail on tables without `tbody` tag** HTML tables may sometimes just contain headers without body (`tbody` tag)

## 0.10.24

### Enhancements

* **Improve natural reading order** Some `OCR` elements with only spaces in the text have full-page width in the bounding box, which causes the `xycut` sorting to not work as expected. Now the logic to parse OCR results removes any elements with only spaces (more than one space).
* **Ingest compression utilities and fsspec connector support** Generic utility code added to handle files that get pulled from a source connector that are either tar or zip compressed and uncompress them locally. This is then processed using a local source connector. Currently this functionality has been incorporated into the fsspec connector and all those inheriting from it (currently: Azure Blob Storage, Google Cloud Storage, S3, Box, and Dropbox).
* **Ingest destination connectors support for writing raw list of elements** Along with the default write method used in the ingest pipeline to write the json content associated with the ingest docs, each destination connector can now also write a raw list of elements to the desired downstream location without having an ingest doc associated with it.

### Features

* **Adds element type percent match function** In order to evaluate the element type extracted, we add a function that calculates the matched percentage between two frequency dictionary.

### Fixes

* **Fix paddle model file not discoverable** Fixes issue where ocr_models/paddle_ocr.py file is not discoverable on PyPI by adding
  an `__init__.py` file under the folder.
* **Chipper v2 Fixes** Includes fix for a memory leak and rare last-element bbox fix. (unstructured-inference==0.7.7)
* **Fix image resizing issue** Includes fix related to resizing images in the tables pipeline. (unstructured-inference==0.7.6)

## 0.10.23

### Enhancements

* **Add functionality to limit precision when serializing to json** Precision for `points` is limited to 1 decimal point if coordinates["system"] == "PixelSpace" (otherwise 2 decimal points?). Precision for `detection_class_prob` is limited to 5 decimal points.
* **Fix csv file detection logic when mime-type is text/plain** Previously the logic to detect csv file type was considering only first row's comma count comparing with the header_row comma count and both the rows being same line the result was always true, Now the logic is changed to consider the comma's count for all the lines except first line and compare with header_row comma count.
* **Improved inference speed for Chipper V2** API requests with 'hi_res_model_name=chipper' now have ~2-3x faster responses.

### Features

### Fixes

* **Cleans up temporary files after conversion** Previously a file conversion utility was leaving temporary files behind on the filesystem without removing them when no longer needed. This fix helps prevent an accumulation of temporary files taking up excessive disk space.
* **Fixes `under_non_alpha_ratio` dividing by zero** Although this function guarded against a specific cause of division by zero, there were edge cases slipping through like strings with only whitespace. This update more generally prevents the function from performing a division by zero.
* **Fix languages default** Previously the default language was being set to English when elements didn't have text or if langdetect could not detect the language. It now defaults to None so there is not misleading information about the language detected.
* **Fixes recursion limit error that was being raised when partitioning Excel documents of a certain size** Previously we used a recursive method to find subtables within an excel sheet. However this would run afoul of Python's recursion depth limit when there was a contiguous block of more than 1000 cells within a sheet. This function has been updated to use the NetworkX library which avoids Python recursion issues.

## 0.10.22

### Enhancements

* **bump `unstructured-inference` to `0.7.3`** The updated version of `unstructured-inference` supports a new version of the Chipper model, as well as a cleaner schema for its output classes. Support is included for new inference features such as hierarchy and ordering.
* **Expose skip_infer_table_types in ingest CLI.** For each connector a new `--skip-infer-table-types` parameter was added to map to the `skip_infer_table_types` partition argument. This gives more granular control to unstructured-ingest users, allowing them to specify the file types for which we should attempt table extraction.
* **Add flag to ingest CLI to raise error if any single doc fails in pipeline** Currently if a single doc fails in the pipeline, the whole thing halts due to the error. This flag defaults to log an error but continue with the docs it can.
* **Emit hyperlink metadata for DOCX file-type.** DOCX partitioner now adds `metadata.links`, `metadata.link_texts` and `metadata.link_urls` for elements that contain a hyperlink that points to an external resource. So-called "jump" links pointing to document internal locations (such as those found in a table-of-contents "jumping" to a chapter or section) are excluded.

### Features

* **Add `elements_to_text` as a staging helper function** In order to get a single clean text output from unstructured for metric calculations, automate the process of extracting text from elements using this function.
* **Adds permissions(RBAC) data ingestion functionality for the Sharepoint connector.** Problem: Role based access control is an important component in many data storage systems. Users may need to pass permissions (RBAC) data to downstream systems when ingesting data. Feature: Added permissions data ingestion functionality to the Sharepoint connector.

### Fixes

* **Fixes PDF list parsing creating duplicate list items** Previously a bug in PDF list item parsing caused removal of other elements and duplication of the list item
* **Fixes duplicated elements** Fixes issue where elements are duplicated when embeddings are generated. This will allow users to generate embeddings for their list of Elements without duplicating/breaking the orginal content.
* **Fixes failure when flagging for embeddings through unstructured-ingest** Currently adding the embedding parameter to any connector results in a failure on the copy stage. This is resolves the issue by adding the IngestDoc to the context map in the embedding node's `run` method. This allows users to specify that connectors fetch embeddings without failure.
* **Fix ingest pipeline reformat nodes not discoverable** Fixes issue where  reformat nodes raise ModuleNotFoundError on import. This was due to the directory was missing `__init__.py` in order to make it discoverable.
* **Fix default language in ingest CLI** Previously the default was being set to english which injected potentially incorrect information to downstream language detection libraries. By setting the default to None allows those libraries to better detect what language the text is in the doc being processed.

## 0.10.21

* **Adds Scarf analytics**.

## 0.10.20

### Enhancements

* **Add document level language detection functionality.** Adds the "auto" default for the languages param to all partitioners. The primary language present in the document is detected using the `langdetect` package. Additional param `detect_language_per_element` is also added for partitioners that return multiple elements. Defaults to `False`.
* **Refactor OCR code** The OCR code for entire page is moved from unstructured-inference to unstructured. On top of continuing support for OCR language parameter, we also support two OCR processing modes, "entire_page" or "individual_blocks".
* **Align to top left when shrinking bounding boxes for `xy-cut` sorting:** Update `shrink_bbox()` to keep top left rather than center.
* **Add visualization script to annotate elements** This script is often used to analyze/visualize elements with coordinates (e.g. partition_pdf()).
* **Adds data source properties to the Jira, Github and Gitlab connectors** These properties (date_created, date_modified, version, source_url, record_locator) are written to element metadata during ingest, mapping elements to information about the document source from which they derive. This functionality enables downstream applications to reveal source document applications, e.g. a link to a GDrive doc, Salesforce record, etc.
* **Improve title detection in pptx documents** The default title textboxes on a pptx slide are now categorized as titles.
* **Improve hierarchy detection in pptx documents** List items, and other slide text are properly nested under the slide title. This will enable better chunking of pptx documents.
* **Refactor of the ingest cli workflow** The refactored approach uses a dynamically set pipeline with a snapshot along each step to save progress and accommodate continuation from a snapshot if an error occurs. This also allows the pipeline to dynamically assign any number of steps to modify the partitioned content before it gets written to a destination.
* **Applies `max_characters=<n>` argument to all element types in `add_chunking_strategy` decorator** Previously this argument was only utilized in chunking Table elements and now applies to all partitioned elements if `add_chunking_strategy` decorator is utilized, further preparing the elements for downstream processing.
* **Add common retry strategy utilities for unstructured-ingest** Dynamic retry strategy with exponential backoff added to Notion source connector.
*

### Features

* **Adds `bag_of_words` and `percent_missing_text` functions** In order to count the word frequencies in two input texts and calculate the percentage of text missing relative to the source document.
* **Adds `edit_distance` calculation metrics** In order to benchmark the cleaned, extracted text with unstructured, `edit_distance` (`Levenshtein distance`) is included.
* **Adds detection_origin field to metadata** Problem: Currently isn't an easy way to find out how an element was created. With this change that information is added. Importance: With this information the developers and users are now able to know how an element was created to make decisions on how to use it. In order tu use this feature
  setting UNSTRUCTURED_INCLUDE_DEBUG_METADATA=true is needed.
* **Adds a function that calculates frequency of the element type and its depth** To capture the accuracy of element type extraction, this function counts the occurrences of each unique element type with its depth for use in element metrics.

### Fixes

* **Fix zero division error in annotation bbox size** This fixes the bug where we find annotation bboxes realted to an element that need to divide the intersection size between annotation bbox and element bbox by the size of the annotation bbox
* **Fix prevent metadata module from importing dependencies from unnecessary modules** Problem: The `metadata` module had several top level imports that were only used in and applicable to code related to specific document types, while there were many general-purpose functions. As a result, general-purpose functions couldn't be used without unnecessary dependencies being installed. Fix: moved 3rd party dependency top level imports to inside the functions in which they are used and applied a decorator to check that the dependency is installed and emit a helpful error message if not.
* **Fixes category_depth None value for Title elements** Problem: `Title` elements from `chipper` get `category_depth`= None even when `Headline` and/or `Subheadline` elements are present in the same page. Fix: all `Title` elements with `category_depth` = None should be set to have a depth of 0 instead iff there are `Headline` and/or `Subheadline` element-types present. Importance: `Title` elements should be equivalent html `H1` when nested headings are present; otherwise, `category_depth` metadata can result ambiguous within elements in a page.
* **Tweak `xy-cut` ordering output to be more column friendly** This results in the order of elements more closely reflecting natural reading order which benefits downstream applications. While element ordering from `xy-cut` is usually mostly correct when ordering multi-column documents, sometimes elements from a RHS column will appear before elements in a LHS column. Fix: add swapped `xy-cut` ordering by sorting by X coordinate first and then Y coordinate.
* **Fixes badly initialized Formula** Problem: YoloX contain new types of elements, when loading a document that contain formulas a new element of that class
  should be generated, however the Formula class inherits from Element instead of Text. After this change the element is correctly created with the correct class
  allowing the document to be loaded. Fix: Change parent class for Formula to Text. Importance: Crucial to be able to load documents that contain formulas.
* **Fixes pdf uri error** An error was encountered when URI type of `GoToR` which refers to pdf resources outside of its own was detected since no condition catches such case. The code is fixing the issue by initialize URI before any condition check.

## 0.10.19

### Enhancements

* **Adds XLSX document level language detection** Enhancing on top of language detection functionality in previous release, we now support language detection within `.xlsx` file type at Element level.
* **bump `unstructured-inference` to `0.6.6`** The updated version of `unstructured-inference` makes table extraction in `hi_res` mode configurable to fine tune table extraction performance; it also improves element detection by adding a deduplication post processing step in the `hi_res` partitioning of pdfs and images.
* **Detect text in HTML Heading Tags as Titles** This will increase the accuracy of hierarchies in HTML documents and provide more accurate element categorization. If text is in an HTML heading tag and is not a list item, address, or narrative text, categorize it as a title.
* **Update python-based docs** Refactor docs to use the actual unstructured code rather than using the subprocess library to run the cli command itself.
* **Adds Table support for the `add_chunking_strategy` decorator to partition functions.** In addition to combining elements under Title elements, user's can now specify the `max_characters=<n>` argument to chunk Table elements into TableChunk elements with `text` and `text_as_html` of length `<n>` characters. This means partitioned Table results are ready for use in downstream applications without any post processing.
* **Expose endpoint url for s3 connectors** By allowing for the endpoint url to be explicitly overwritten, this allows for any non-AWS data providers supporting the s3 protocol to be supported (i.e. minio).

### Features

* **change default `hi_res` model for pdf/image partition to `yolox`** Now partitioning pdf/image using `hi_res` strategy utilizes `yolox_quantized` model isntead of `detectron2_onnx` model. This new default model has better recall for tables and produces more detailed categories for elements.
* **XLSX can now reads subtables within one sheet** Problem: Many .xlsx files are not created to be read as one full table per sheet. There are subtables, text and header along with more informations to extract from each sheet. Feature: This `partition_xlsx` now can reads subtable(s) within one .xlsx sheet, along with extracting other title and narrative texts. Importance: This enhance the power of .xlsx reading to not only one table per sheet, allowing user to capture more data tables from the file, if exists.
* **Update Documentation on Element Types and Metadata**: We have updated the documentation according to the latest element types and metadata. It includes the common and additional metadata provided by the Partitions and Connectors.

### Fixes

* **Fixes partition_pdf is_alnum reference bug** Problem: The `partition_pdf` when attempt to get bounding box from element experienced a reference before assignment error when the first object is not text extractable.  Fix: Switched to a flag when the condition is met. Importance: Crucial to be able to partition with pdf.
* **Fix various cases of HTML text missing after partition**
  Problem: Under certain circumstances, text immediately after some HTML tags will be misssing from partition result.
  Fix: Updated code to deal with these cases.
  Importance: This will ensure the correctness when partitioning HTML and Markdown documents.
* **Fixes chunking when `detection_class_prob` appears in Element metadata** Problem: when `detection_class_prob` appears in Element metadata, Elements will only be combined by chunk_by_title if they have the same `detection_class_prob` value (which is rare). This is unlikely a case we ever need to support and most often results in no chunking. Fix: `detection_class_prob` is included in the chunking list of metadata keys excluded for similarity comparison. Importance: This change allows `chunk_by_title` to operate as intended for documents which include `detection_class_prob` metadata in their Elements.

## 0.10.18

### Enhancements

* **Better detection of natural reading order in images and PDF's** The elements returned by partition better reflect natural reading order in some cases, particularly in complicated multi-column layouts, leading to better chunking and retrieval for downstream applications. Achieved by improving the `xy-cut` sorting to preprocess bboxes, shrinking all bounding boxes by 90% along x and y axes (still centered around the same center point), which allows projection lines to be drawn where not possible before if layout bboxes overlapped.
* **Improves `partition_xml` to be faster and more memory efficient when partitioning large XML files** The new behavior is to partition iteratively to prevent loading the entire XML tree into memory at once in most use cases.
* **Adds data source properties to SharePoint, Outlook, Onedrive, Reddit, Slack, DeltaTable connectors** These properties (date_created, date_modified, version, source_url, record_locator) are written to element metadata during ingest, mapping elements to information about the document source from which they derive. This functionality enables downstream applications to reveal source document applications, e.g. a link to a GDrive doc, Salesforce record, etc.
* **Add functionality to save embedded images in PDF's separately as images** This allows users to save embedded images in PDF's separately as images, given some directory path. The saved image path is written to the metadata for the Image element. Downstream applications may benefit by providing users with image links from relevant "hits."
* **Azure Cognite Search destination connector** New Azure Cognitive Search destination connector added to ingest CLI.  Users may now use `unstructured-ingest` to write partitioned data from over 20 data sources (so far) to an Azure Cognitive Search index.
* **Improves salesforce partitioning** Partitions Salesforce data as xlm instead of text for improved detail and flexibility. Partitions htmlbody instead of textbody for Salesforce emails. Importance: Allows all Salesforce fields to be ingested and gives Salesforce emails more detailed partitioning.
* **Add document level language detection functionality.** Introduces the "auto" default for the languages param, which then detects the languages present in the document using the `langdetect` package. Adds the document languages as ISO 639-3 codes to the element metadata. Implemented only for the partition_text function to start.
* **PPTX partitioner refactored in preparation for enhancement.** Behavior should be unchanged except that shapes enclosed in a group-shape are now included, as many levels deep as required (a group-shape can itself contain a group-shape).
* **Embeddings support for the SharePoint SourceConnector via unstructured-ingest CLI** The SharePoint connector can now optionally create embeddings from the elements it pulls out during partition and upload those embeddings to Azure Cognitive Search index.
* **Improves hierarchy from docx files by leveraging natural hierarchies built into docx documents**  Hierarchy can now be detected from an indentation level for list bullets/numbers and by style name (e.g. Heading 1, List Bullet 2, List Number).
* **Chunking support for the SharePoint SourceConnector via unstructured-ingest CLI** The SharePoint connector can now optionally chunk the elements pulled out during partition via the chunking unstructured brick. This can be used as a stage before creating embeddings.

### Features

* **Adds `links` metadata in `partition_pdf` for `fast` strategy.** Problem: PDF files contain rich information and hyperlink that Unstructured did not captured earlier. Feature: `partition_pdf` now can capture embedded links within the file along with its associated text and page number. Importance: Providing depth in extracted elements give user a better understanding and richer context of documents. This also enables user to map to other elements within the document if the hyperlink is refered internally.
* **Adds the embedding module to be able to embed Elements** Problem: Many NLP applications require the ability to represent parts of documents in a semantic way. Until now, Unstructured did not have text embedding ability within the core library. Feature: This embedding module is able to track embeddings related data with a class, embed a list of elements, and return an updated list of Elements with the *embeddings* property. The module is also able to embed query strings. Importance: Ability to embed documents or parts of documents will enable users to make use of these semantic representations in different NLP applications, such as search, retrieval, and retrieval augmented generation.

### Fixes

* **Fixes a metadata source serialization bug** Problem: In unstructured elements, when loading an elements json file from the disk, the data_source attribute is assumed to be an instance of DataSourceMetadata and the code acts based on that. However the loader did not satisfy the assumption, and loaded it as a dict instead, causing an error. Fix: Added necessary code block to initialize a DataSourceMetadata object, also refactored DataSourceMetadata.from_dict() method to remove redundant code. Importance: Crucial to be able to load elements (which have data_source fields) from json files.
* **Fixes issue where unstructured-inference was not getting updated** Problem: unstructured-inference was not getting upgraded to the version to match unstructured release when doing a pip install.  Solution: using `pip install unstructured[all-docs]` it will now upgrade both unstructured and unstructured-inference. Importance: This will ensure that the inference library is always in sync with the unstructured library, otherwise users will be using outdated libraries which will likely lead to unintended behavior.
* **Fixes SharePoint connector failures if any document has an unsupported filetype** Problem: Currently the entire connector ingest run fails if a single IngestDoc has an unsupported filetype. This is because a ValueError is raised in the IngestDoc's `__post_init__`. Fix: Adds a try/catch when the IngestConnector runs get_ingest_docs such that the error is logged but all processable documents->IngestDocs are still instantiated and returned. Importance: Allows users to ingest SharePoint content even when some files with unsupported filetypes exist there.
* **Fixes Sharepoint connector server_path issue** Problem: Server path for the Sharepoint Ingest Doc was incorrectly formatted, causing issues while fetching pages from the remote source. Fix: changes formatting of remote file path before instantiating SharepointIngestDocs and appends a '/' while fetching pages from the remote source. Importance: Allows users to fetch pages from Sharepoint Sites.
* **Fixes Sphinx errors.** Fixes errors when running Sphinx `make html` and installs library to suppress warnings.
* **Fixes a metadata backwards compatibility error** Problem: When calling `partition_via_api`, the hosted api may return an element schema that's newer than the current `unstructured`. In this case, metadata fields were added which did not exist in the local `ElementMetadata` dataclass, and `__init__()` threw an error. Fix: remove nonexistent fields before instantiating in `ElementMetadata.from_json()`. Importance: Crucial to avoid breaking changes when adding fields.
* **Fixes issue with Discord connector when a channel returns `None`** Problem: Getting the `jump_url` from a nonexistent Discord `channel` fails. Fix: property `jump_url` is now retrieved within the same context as the messages from the channel. Importance: Avoids cascading issues when the connector fails to fetch information about a Discord channel.
* **Fixes occasionally SIGABTR when writing table with `deltalake` on Linux** Problem: occasionally on Linux ingest can throw a `SIGABTR` when writing `deltalake` table even though the table was written correctly. Fix: put the writing function into a `Process` to ensure its execution to the fullest extent before returning to the main process. Importance: Improves stability of connectors using `deltalake`
* **Fixes badly initialized Formula** Problem: YoloX contain new types of elements, when loading a document that contain formulas a new element of that class should be generated, however the Formula class inherits from Element instead of Text. After this change the element is correctly created with the correct class allowing the document to be loaded. Fix: Change parent class for Formula to Text. Importance: Crucial to be able to load documents that contain formulas.

## 0.10.16

### Enhancements

* **Adds data source properties to Airtable, Confluence, Discord, Elasticsearch, Google Drive, and Wikipedia connectors** These properties (date_created, date_modified, version, source_url, record_locator) are written to element metadata during ingest, mapping elements to information about the document source from which they derive. This functionality enables downstream applications to reveal source document applications, e.g. a link to a GDrive doc, Salesforce record, etc.
* **DOCX partitioner refactored in preparation for enhancement.** Behavior should be unchanged except in multi-section documents containing different headers/footers for different sections. These will now emit all distinct headers and footers encountered instead of just those for the last section.
* **Add a function to map between Tesseract and standard language codes.** This allows users to input language information to the `languages` param in any Tesseract-supported langcode or any ISO 639 standard language code.
* **Add document level language detection functionality.** Introduces the "auto" default for the languages param, which then detects the languages present in the document using the `langdetect` package. Implemented only for the partition_text function to start.

### Features

### Fixes

* ***Fixes an issue that caused a partition error for some PDF's.** Fixes GH Issue 1460 by bypassing a coordinate check if an element has invalid coordinates.

## 0.10.15

### Enhancements

* **Support for better element categories from the next-generation image-to-text model ("chipper").** Previously, not all of the classifications from Chipper were being mapped to proper `unstructured` element categories so the consumer of the library would see many `UncategorizedText` elements. This fixes the issue, improving the granularity of the element categories outputs for better downstream processing and chunking. The mapping update is:
  * "Threading": `NarrativeText`
  * "Form": `NarrativeText`
  * "Field-Name": `Title`
  * "Value": `NarrativeText`
  * "Link": `NarrativeText`
  * "Headline": `Title` (with `category_depth=1`)
  * "Subheadline": `Title` (with `category_depth=2`)
  * "Abstract": `NarrativeText`
* **Better ListItem grouping for PDF's (fast strategy).** The `partition_pdf` with `fast` strategy previously broke down some numbered list item lines as separate elements. This enhancement leverages the x,y coordinates and bbox sizes to help decide whether the following chunk of text is a continuation of the immediate previous detected ListItem element or not, and not detect it as its own non-ListItem element.
* **Fall back to text-based classification for uncategorized Layout elements for Images and PDF's**. Improves element classification by running existing text-based rules on previously `UncategorizedText` elements.
* **Adds table partitioning for Partitioning for many doc types including: .html, .epub., .md, .rst, .odt, and .msg.** At the core of this change is the .html partition functionality, which is leveraged by the other effected doc types. This impacts many scenarios where `Table` Elements are now propery extracted.
* **Create and add `add_chunking_strategy` decorator to partition functions.** Previously, users were responsible for their own chunking after partitioning elements, often required for downstream applications. Now, individual elements may be combined into right-sized chunks where min and max character size may be specified if `chunking_strategy=by_title`. Relevant elements are grouped together for better downstream results. This enables users immediately use partitioned results effectively in downstream applications (e.g. RAG architecture apps) without any additional post-processing.
* **Adds `languages` as an input parameter and marks `ocr_languages` kwarg for deprecation in pdf, image, and auto partitioning functions.** Previously, language information was only being used for Tesseract OCR for image-based documents and was in a Tesseract specific string format, but by refactoring into a list of standard language codes independent of Tesseract, the `unstructured` library will better support `languages` for other non-image pipelines and/or support for other OCR engines.
* **Removes `UNSTRUCTURED_LANGUAGE` env var usage and replaces `language` with `languages` as an input parameter to unstructured-partition-text_type functions.** The previous parameter/input setup was not user-friendly or scalable to the variety of elements being processed. By refactoring the inputted language information into a list of standard language codes, we can support future applications of the element language such as detection, metadata, and multi-language elements. Now, to skip English specific checks, set the `languages` parameter to any non-English language(s).
* **Adds `xlsx` and `xls` filetype extensions to the `skip_infer_table_types` default list in `partition`.** By adding these file types to the input parameter these files should not go through table extraction. Users can still specify if they would like to extract tables from these filetypes, but will have to set the `skip_infer_table_types` to exclude the desired filetype extension. This avoids mis-representing complex spreadsheets where there may be multiple sub-tables and other content.
* **Better debug output related to sentence counting internals**. Clarify message when sentence is not counted toward sentence count because there aren't enough words, relevant for developers focused on `unstructured`s NLP internals.
* **Faster ocr_only speed for partitioning PDF and images.** Use `unstructured_pytesseract.run_and_get_multiple_output` function to reduce the number of calls to `tesseract` by half when partitioning pdf or image with `tesseract`
* **Adds data source properties to fsspec connectors** These properties (date_created, date_modified, version, source_url, record_locator) are written to element metadata during ingest, mapping elements to information about the document source from which they derive. This functionality enables downstream applications to reveal source document applications, e.g. a link to a GDrive doc, Salesforce record, etc.
* **Add delta table destination connector** New delta table destination connector added to ingest CLI.  Users may now use `unstructured-ingest` to write partitioned data from over 20 data sources (so far) to a Delta Table.
* **Rename to Source and Destination Connectors in the Documentation.** Maintain naming consistency between Connectors codebase and documentation with the first addition to a destination connector.
* **Non-HTML text files now return unstructured-elements as opposed to HTML-elements.** Previously the text based files that went through `partition_html` would return HTML-elements but now we preserve the format from the input using `source_format` argument in the partition call.
* **Adds `PaddleOCR` as an optional alternative to `Tesseract`** for OCR in processing of PDF or Image files, it is installable via the `makefile` command `install-paddleocr`. For experimental purposes only.
* **Bump unstructured-inference** to 0.5.28. This version bump markedly improves the output of table data, rendered as `metadata.text_as_html` in an element. These changes include:
  * add env variable `ENTIRE_PAGE_OCR` to specify using paddle or tesseract on entire page OCR
  * table structure detection now pads the input image by 25 pixels in all 4 directions to improve its recall (0.5.27)
  * support paddle with both cpu and gpu and assume it is pre-installed (0.5.26)
  * fix a bug where `cells_to_html` doesn't handle cells spanning multiple rows properly (0.5.25)
  * remove `cv2` preprocessing step before OCR step in table transformer (0.5.24)

### Features

* **Adds element metadata via `category_depth` with default value None**.
  * This additional metadata is useful for vectordb/LLM, chunking strategies, and retrieval applications.
* **Adds a naive hierarchy for elements via a `parent_id` on the element's metadata**
  * Users will now have more metadata for implementing vectordb/LLM chunking strategies. For example, text elements could be queried by their preceding title element.
  * Title elements created from HTML headings will properly nest

### Fixes

* **`add_pytesseract_bboxes_to_elements` no longer returns `nan` values**. The function logic is now broken into new methods
  `_get_element_box` and `convert_multiple_coordinates_to_new_system`
* **Selecting a different model wasn't being respected when calling `partition_image`.** Problem: `partition_pdf` allows for passing a `model_name` parameter. Given the similarity between the image and PDF pipelines, the expected behavior is that `partition_image` should support the same parameter, but `partition_image` was unintentionally not passing along its `kwargs`. This was corrected by adding the kwargs to the downstream call.
* **Fixes a chunking issue via dropping the field "coordinates".** Problem: chunk_by_title function was chunking each element to its own individual chunk while it needed to group elements into a fewer number of chunks. We've discovered that this happens due to a metadata matching logic in chunk_by_title function, and discovered that elements with different metadata can't be put into the same chunk. At the same time, any element with "coordinates" essentially had different metadata than other elements, due each element locating in different places and having different coordinates. Fix: That is why we have included the key "coordinates" inside a list of excluded metadata keys, while doing this "metadata_matches" comparision. Importance: This change is crucial to be able to chunk by title for documents which include "coordinates" metadata in their elements.

## 0.10.14

### Enhancements

* Update all connectors to use new downstream architecture
  * New click type added to parse comma-delimited string inputs
  * Some CLI options renamed

### Features

### Fixes

## 0.10.13

### Enhancements

* Updated documentation: Added back support doc types for partitioning, more Python codes in the API page,  RAG definition, and use case.
* Updated Hi-Res Metadata: PDFs and Images using Hi-Res strategy now have layout model class probabilities added ot metadata.
* Updated the `_detect_filetype_from_octet_stream()` function to use libmagic to infer the content type of file when it is not a zip file.
* Tesseract minor version bump to 5.3.2

### Features

* Add Jira Connector to be able to pull issues from a Jira organization
* Add `clean_ligatures` function to expand ligatures in text

### Fixes

* `partition_html` breaks on `<br>` elements.
* Ingest error handling to properly raise errors when wrapped
* GH issue 1361: fixes a sortig error that prevented some PDF's from being parsed
* Bump unstructured-inference
  * Brings back embedded images in PDF's (0.5.23)

## 0.10.12

### Enhancements

* Removed PIL pin as issue has been resolved upstream
* Bump unstructured-inference
  * Support for yolox_quantized layout detection model (0.5.20)
* YoloX element types added

### Features

* Add Salesforce Connector to be able to pull Account, Case, Campaign, EmailMessage, Lead

### Fixes

* Bump unstructured-inference
  * Avoid divide-by-zero errors swith `safe_division` (0.5.21)

## 0.10.11

### Enhancements

* Bump unstructured-inference
  * Combine entire-page OCR output with layout-detected elements, to ensure full coverage of the page (0.5.19)

### Features

* Add in ingest cli s3 writer

### Fixes

* Fix a bug where `xy-cut` sorting attemps to sort elements without valid coordinates; now xy cut sorting only works when **all** elements have valid coordinates

## 0.10.10

### Enhancements

* Adds `text` as an input parameter to `partition_xml`.
* `partition_xml` no longer runs through `partition_text`, avoiding incorrect splitting
  on carriage returns in the XML. Since `partition_xml` no longer calls `partition_text`,
  `min_partition` and `max_partition` are no longer supported in `partition_xml`.
* Bump `unstructured-inference==0.5.18`, change non-default detectron2 classification threshold
* Upgrade base image from rockylinux 8 to rockylinux 9
* Serialize IngestDocs to JSON when passing to subprocesses

### Features

### Fixes

- Fix a bug where mismatched `elements` and `bboxes` are passed into `add_pytesseract_bbox_to_elements`

## 0.10.9

### Enhancements

* Fix `test_json` to handle only non-extra dependencies file types (plain-text)

### Features

* Adds `chunk_by_title` to break a document into sections based on the presence of `Title`
  elements.
* add new extraction function `extract_image_urls_from_html` to extract all img related URL from html text.

### Fixes

* Make cv2 dependency optional
* Edit `add_pytesseract_bbox_to_elements`'s (`ocr_only` strategy) `metadata.coordinates.points` return type to `Tuple` for consistency.
* Re-enable test-ingest-confluence-diff for ingest tests
* Fix syntax for ingest test check number of files
* Fix csv and tsv partitioners loosing the first line of the files when creating elements

## 0.10.8

### Enhancements

* Release docker image that installs Python 3.10 rather than 3.8

### Features

### Fixes

## 0.10.7

### Enhancements

### Features

### Fixes

* Remove overly aggressive ListItem chunking for images and PDF's which typically resulted in inchorent elements.

## 0.10.6

### Enhancements

* Enable `partition_email` and `partition_msg` to detect if an email is PGP encryped. If
  and email is PGP encryped, the functions will return an empy list of elements and
  emit a warning about the encrypted content.
* Add threaded Slack conversations into Slack connector output
* Add functionality to sort elements using `xy-cut` sorting approach in `partition_pdf` for `hi_res` and `fast` strategies
* Bump unstructured-inference
  * Set OMP_THREAD_LIMIT to 1 if not set for better tesseract perf (0.5.17)

### Features

* Extract coordinates from PDFs and images when using OCR only strategy and add to metadata

### Fixes

* Update `partition_html` to respect the order of `<pre>` tags.
* Fix bug in `partition_pdf_or_image` where two partitions were called if `strategy == "ocr_only"`.
* Bump unstructured-inference
  * Fix issue where temporary files were being left behind (0.5.16)
* Adds deprecation warning for the `file_filename` kwarg to `partition`, `partition_via_api`,
  and `partition_multiple_via_api`.
* Fix documentation build workflow by pinning dependencies

## 0.10.5

### Enhancements

* Create new CI Pipelines
  - Checking text, xml, email, and html doc tests against the library installed without extras
  - Checking each library extra against their respective tests
* `partition` raises an error and tells the user to install the appropriate extra if a filetype
  is detected that is missing dependencies.
* Add custom errors to ingest
* Bump `unstructured-ingest==0.5.15`
  - Handle an uncaught TesseractError (0.5.15)
  - Add TIFF test file and TIFF filetype to `test_from_image_file` in `test_layout` (0.5.14)
* Use `entire_page` ocr mode for pdfs and images
* Add notes on extra installs to docs
* Adds ability to reuse connections per process in unstructured-ingest

### Features

* Add delta table connector

### Fixes

## 0.10.4

* Pass ocr_mode in partition_pdf and set the default back to individual pages for now
* Add diagrams and descriptions for ingest design in the ingest README

### Features

* Supports multipage TIFF image partitioning

### Fixes

## 0.10.2

### Enhancements

* Bump unstructured-inference==0.5.13:
  - Fix extracted image elements being included in layout merge, addresses the issue
    where an entire-page image in a PDF was not passed to the layout model when using hi_res.

### Features

### Fixes

## 0.10.1

### Enhancements

* Bump unstructured-inference==0.5.12:
  - fix to avoid trace for certain PDF's (0.5.12)
  - better defaults for DPI for hi_res and  Chipper (0.5.11)
  - implement full-page OCR (0.5.10)

### Features

### Fixes

* Fix dead links in repository README (Quick Start > Install for local development, and Learn more > Batch Processing)
* Update document dependencies to include tesseract-lang for additional language support (required for tests to pass)

## 0.10.0

### Enhancements

* Add `include_header` kwarg to `partition_xlsx` and change default behavior to `True`
* Update the `links` and `emphasized_texts` metadata fields

### Features

### Fixes

## 0.9.3

### Enhancements

* Pinned dependency cleanup.
* Update `partition_csv` to always use `soupparser_fromstring` to parse `html text`
* Update `partition_tsv` to always use `soupparser_fromstring` to parse `html text`
* Add `metadata.section` to capture epub table of contents data
* Add `unique_element_ids` kwarg to partition functions. If `True`, will use a UUID
  for element IDs instead of a SHA-256 hash.
* Update `partition_xlsx` to always use `soupparser_fromstring` to parse `html text`
* Add functionality to switch `html` text parser based on whether the `html` text contains emoji
* Add functionality to check if a string contains any emoji characters
* Add CI tests around Notion

### Features

* Add Airtable Connector to be able to pull views/tables/bases from an Airtable organization

### Fixes

* fix pdf partition of list items being detected as titles in OCR only mode
* make notion module discoverable
* fix emails with `Content-Distribution: inline` and `Content-Distribution: attachment` with no filename
* Fix email attachment filenames which had `=` in the filename itself

## 0.9.2

### Enhancements

* Update table extraction section in API documentation to sync with change in Prod API
* Update Notion connector to extract to html
* Added UUID option for `element_id`
* Bump unstructured-inference==0.5.9:
  - better caching of models
  - another version of detectron2 available, though the default layout model is unchanged
* Added UUID option for element_id
* Added UUID option for element_id
* CI improvements to run ingest tests in parallel

### Features

* Adds Sharepoint connector.

### Fixes

* Bump unstructured-inference==0.5.9:
  - ignores Tesseract errors where no text is extracted for tiles that indeed, have no text

## 0.9.1

### Enhancements

* Adds --partition-pdf-infer-table-structure to unstructured-ingest.
* Enable `partition_html` to skip headers and footers with the `skip_headers_and_footers` flag.
* Update `partition_doc` and `partition_docx` to track emphasized texts in the output
* Adds post processing function `filter_element_types`
* Set the default strategy for partitioning images to `hi_res`
* Add page break parameter section in API documentation to sync with change in Prod API
* Update `partition_html` to track emphasized texts in the output
* Update `XMLDocument._read_xml` to create `<p>` tag element for the text enclosed in the `<pre>` tag
* Add parameter `include_tail_text` to `_construct_text` to enable (skip) tail text inclusion
* Add Notion connector

### Features

### Fixes

* Remove unused `_partition_via_api` function
* Fixed emoji bug in `partition_xlsx`.
* Pass `file_filename` metadata when partitioning file object
* Skip ingest test on missing Slack token
* Add Dropbox variables to CI environments
* Remove default encoding for ingest
* Adds new element type `EmailAddress` for recognising email address in the  text
* Simplifies `min_partition` logic; makes partitions falling below the `min_partition`
  less likely.
* Fix bug where ingest test check for number of files fails in smoke test
* Fix unstructured-ingest entrypoint failure

## 0.9.0

### Enhancements

* Dependencies are now split by document type, creating a slimmer base installation.

## 0.8.8

### Enhancements

### Features

### Fixes

* Rename "date" field to "last_modified"
* Adds Box connector

### Fixes

## 0.8.7

### Enhancements

* Put back useful function `split_by_paragraph`

### Features

### Fixes

* Fix argument order in NLTK download step

## 0.8.6

### Enhancements

### Features

### Fixes

* Remove debug print lines and non-functional code

## 0.8.5

### Enhancements

* Add parameter `skip_infer_table_types` to enable (skip) table extraction for other doc types
* Adds optional Unstructured API unit tests in CI
* Tracks last modified date for all document types.
* Add auto_paragraph_grouper to detect new-line and blank-line new paragraph for .txt files.
* refactor the ingest cli to better support expanding supported connectors

## 0.8.3

### Enhancements

### Features

### Fixes

* NLTK now only gets downloaded if necessary.
* Handling for empty tables in Word Documents and PowerPoints.

## 0.8.4

### Enhancements

* Additional tests and refactor of JSON detection.
* Update functionality to retrieve image metadata from a page for `document_to_element_list`
* Links are now tracked in `partition_html` output.
* Set the file's current position to the beginning after reading the file in `convert_to_bytes`
* Add `min_partition` kwarg to that combines elements below a specified threshold and modifies splitting of strings longer than max partition so words are not split.
* set the file's current position to the beginning after reading the file in `convert_to_bytes`
* Add slide notes to pptx
* Add `--encoding` directive to ingest
* Improve json detection by `detect_filetype`

### Features

* Adds Outlook connector
* Add support for dpi parameter in inference library
* Adds Onedrive connector.
* Add Confluence connector for ingest cli to pull the body text from all documents from all spaces in a confluence domain.

### Fixes

* Fixes issue with email partitioning where From field was being assigned the To field value.
* Use the `image_metadata` property of the `PageLayout` instance to get the page image info in the `document_to_element_list`
* Add functionality to write images to computer storage temporarily instead of keeping them in memory for `ocr_only` strategy
* Add functionality to convert a PDF in small chunks of pages at a time for `ocr_only` strategy
* Adds `.txt`, `.text`, and `.tab` to list of extensions to check if file
  has a `text/plain` MIME type.
* Enables filters to be passed to `partition_doc` so it doesn't error with LibreOffice7.
* Removed old error message that's superseded by `requires_dependencies`.
* Removes using `hi_res` as the default strategy value for `partition_via_api` and `partition_multiple_via_api`

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
