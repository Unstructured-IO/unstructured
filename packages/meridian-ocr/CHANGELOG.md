## 1.6.13

### Fixes
- **Render filled PDF form fields**: `convert_pdf_to_image` now calls `init_forms()` so AcroForm/XFA field values (text typed into fillable fields) are painted into the rendered page image instead of being silently dropped.

## 1.6.12

### Fixes
- **Render rotated PDF pages consistently with extracted text**: `convert_pdf_to_image` no longer re-applies the page `/Rotate` on top of pypdfium2's render (which already produces the display frame), so the rendered image stays in the same coordinate frame as pdfminer's extracted text. For pages with a non-zero `/Rotate`, the dominant text orientation is detected and, when a single 90-degree orientation clearly dominates (configurable via `PDF_ROTATION_DOMINANT_ANGLE_THRESHOLD`), the image is rotated so its text is upright. The applied correction is exposed as `pdf_rotation_correction` in the page image metadata so downstream consumers can keep extracted coordinates aligned.

## 1.6.11

### Enhancement
- Add `table_extraction_method` field to `LayoutElements` and `LayoutElement` to track which algorithm produced a table (grid, tatr, vlm).

## 1.6.10

### Enhancement
- Add Python 3.13 support.

## 1.6.9

### Enhancement
- Restore support for Python 3.11 alongside Python 3.12.

## 1.6.8

### Fix
- Reject PDF pages that would render beyond the configured pixel limit before
  allocating the page bitmap.

## 1.6.7

### Fix
- `get_model` now materializes `LazyDict` model configs into a plain dict before
  unpacking into `initialize(**...)`. Uses `__iter__` + `__getitem__` to avoid
  depending on `Mapping.keys()`, which has been observed to fail at `**`
  unpacking with "argument after ** must be a mapping, not LazyDict" in some
  deployment environments.

## 1.6.6

### Enhancement
- Relax the lower bound of the pandas and numpy dependency

## 1.6.5

### Enhancement
- Store `pdf_rotation` in `page.image_metadata` so downstream consumers can check page rotation after the page image is freed
- Add targeted unittest coverage for PDF page rotation handling in `convert_pdf_to_image`
- Speed up the targeted rotation unittest by isolating the PDF image conversion surface into a lightweight module and mocking the PDFium rendering path for the timing-critical test

## 1.6.4

### Fix
- Apply PDF `/Rotate` metadata during page rendering - pypdfium2's `page.render()` ignores the flag, producing sideways images for rotated pages

## 1.6.3

### Security

- **security:** fix(deps): upgrade vulnerable transitive dependencies [security]

## 1.6.2

### Enhancement
- Make `dpi` an explicit parameter on `convert_pdf_to_image` (default 200) instead of reading from config internally, enabling unstructured to use this as the single source of truth for PDF rendering

## 1.6.1

### Enhancement
- Free intermediate arrays (`origin_img`, `img`, `ort_inputs`, `output`) and PIL pixel buffer at dead points during YoloX `image_processing()` to reduce peak memory during inference

## 1.6.0

### Fix
- Relax `huggingface-hub` lower bound from `>=1.4.1` to `>=0.22.0` (the `>=1.4.1` was an artifact of the uv migration and broke compatibility with `transformers<5.0`)

## 1.5.5

### Enhancement
- Lazy page rendering in `convert_pdf_to_image` to reduce peak memory from O(N pages) to O(1 page)

## 1.5.4

### Enhancement
- Use `np.full()` instead of `np.ones() * scalar` in YoloX preprocessing to avoid a redundant temporary array

## 1.5.3

- Store routing in LayoutElement

## 1.5.2

### Fix
- Switch to PyPI trusted publishing (OIDC) and remove API token auth

## 1.5.1

### Fix
- Add `id-token: write` permission to release workflow for PyPI attestations

## 1.5.0

### Enhancement
- Automate PyPI and Azure Artifacts publishing via GitHub release workflow
- Replace `--frozen` with `--locked` across Makefile and Dockerfile for stricter lockfile validation
- Add `release` dependency group with `twine` for Azure Artifacts upload
- Constrain pillow to >=12.1.1 to address CVE for out-of-bounds write when loading PSD images

## 1.4.0

### Enhancement
- Switch CI runners to `opensource-linux-8core` for faster builds
- Add pytest-xdist parallelization (`-n auto`) to `docker-test` target
- Remove mypy from lint pipeline; ruff covers linting needs sufficiently
- Add `install-lint` target; CI lint job no longer downloads full project dependencies

## 1.3.0

### Enhancement
- Migrate project to native uv with hatchling build backend
- Consolidate all configuration into pyproject.toml
- Replace pip/requirements workflow with uv sync/lock
- Parallelize test runs with pytest-xdist (`-n auto`)

### Breaking
- Drop support for Python 3.10 and 3.11; require Python >=3.12, <3.13

## 1.2.0

### Enhancement
- **Per-model locks for parallel model loading**: Replace single global lock with per-model locks
  - Allows concurrent loading of different models (detectron2, yolox, etc.)
  - 10x+ concurrency improvement in multi-model environments
  - Maintains thread-safe initialization with double-check pattern
  - Backward compatible - no API changes

## 1.1.9

### Fix
- **TableTransformer device_map fix**: Remove device_map parameter to prevent meta tensor errors
  - Device normalization (cuda -> cuda:0) for consistent caching
  - Load models without device_map, use explicit .to(device, dtype=torch.float32)
  - Fixes concurrent PDF processing AssertionError
  - Prevents "Trying to set a tensor of type Float but got Meta" errors
- Use context manager for `pdfium.PdfDocument`

## 1.1.8

- put `pdfium` call behind a thread lock

## 1.1.7

- Update OpenCV-Python to 4.13.0.90 to squash ffmpeg vulnerability CVE-2023-6605

## 1.1.6

- Use inference_config to set default rendering DPI

## 1.1.5

- Render PDF to image using PyPDFium instead of pdf2image, due to much improved performance for certain docs

## 1.1.4

- Constrain urllib3 to urllib3>=2.6.0 to address CVE-2025-66471 and CVE-2025-66418

## 1.1.3

- Constrain fonttools to >=4.60.2 to address CVE-2025-66034

## 1.1.2

* chore(deps): Bump several depedencies to resolve open high CVEs
* fix: Exclude pip and setuptools pinning based on cursor comment
* fix: With the newer version of transformers 4.57.1, the type checking became stricter, and mypy correctly flagged that DetrImageProcessor.from_pretrained() expects str | PathLike[Any], not a model object.
* fix: Update test to explicitly cast numpy array to uint8 for Pillow 12.0.0 compatibility

## 1.1.1

* Add NotImplementedError when trying to single index a TextRegions, reflecting the fact that it won't behave correctly at the moment.

## 1.1.0

* Enhancement: Add `TextSource` to track where the text of an element came from
* Enhancement: Refactor `__post_init__` of `TextRegions` and `LayoutElement` slightly to automate initialization

## 1.0.10

* Remove merging logic that's no longer used

## 1.0.9

* Make OD model loading thread safe

## 1.0.8

* Enhancement: Optimized `zoom_image` (codeflash)
* Enhancement: Optimized `cells_to_html` for an 8% speedup in some cases (codeflash)
* Enhancement: Optimized `outputs_to_objects` for an 88% speedup in some cases (codeflash)

## 1.0.7

* Fix a hardcoded file extension causing confusion in the logs

## 1.0.6

* Add slicing through indexing for vectorized elements

## 1.0.5

* feat: add thread lock to prevent racing condition when instantiating singletons
* feat: parametrize edge config for `DetrImageProcessor` with env variables

## 1.0.4

* feat: use singleton instead of `global` to store shared variables

## 1.0.3

* setting longest_edge=1333 to the table image processor

## 1.0.2

* adding parameter to table image preprocessor related to the image size

## 1.0.1

* fix: moving the table transformer model to device when loading the model instead of once the model is loaded.

## 1.0.0

* feat: support for Python 3.10+; drop support for Python 3.9

## 0.8.11

* feat: remove `donut` model

## 0.8.10

* feat: unpin `numpy` and bump minimum for `onnxruntime` to be compatible with `numpy>=2`

## 0.8.9

* chore: unpin `pdfminer-six` version

## 0.8.8
* fix: pdfminer-six dependencies
* feat: `PageLayout.elements` is now a `cached_property` to reduce unecessary memory and cpu costs

## 0.8.7

* fix: add `password` for PDF

## 0.8.6

* feat: add back `source` to `TextRegions` and `LayoutElements` for backward compatibility

## 0.8.5

* fix: remove `pdfplumber` but include `pdfminer-six==20240706` to update `pdfminer`

## 0.8.4

* feat: add `text_as_html` and `table_as_cells` to `LayoutElements` class as new attributes
* feat: replace the single valueed `source` attribute from `TextRegions` and `LayoutElements` with an array attribute `sources`

## 0.8.3

* fix: removed `layoutelement.from_lp_textblock()` and related tests as it's not used
* fix: update requirements to drop `layoutparser` lib
* fix: update `README.md` to remove layoutparser model zoo support note

## 0.8.2

* fix: fix bug when an empty list is passed into `TextRegions.from_list` triggers `IndexError`
* fix: fix bug when concatenate a list of `LayoutElements` the class id mapping is no properly
  updated

## 0.8.1

* fix: fix list index out of range error caused by calling LayoutElements.from_list() with empty list

## 0.8.0

* fix: fix missing source after cleaning layout elements
* **BREAKING** Remove chipper model

## 0.7.41

* fix: fix incorrect type casting with higher versions of `numpy` when substracting a `float` from an `int` array
* fix: fix a bug where class id 0 becomes class type `None` when calling `LayoutElements.as_list()`

## 0.7.40

* fix: store probabilities with `float` data type instead of `int`

## 0.7.39

* fix: Correctly assign mutable default value to variable in `LayoutElements` class

## 0.7.38

* fix: Correctly assign mutable default value to variable in `TextRegions` class

## 0.7.37

* refactor: remove layout analysis related code
* enhancement: Hide warning about table transformer weights not being loaded
* fix(layout): Use TemporaryDirectory instead of NamedTemporaryFile for Windows support
* refactor: use `numpy` array to store layout elements' information in one single `LayoutElements`
  object instead of using a list of `LayoutElement`

## 0.7.36

fix: add input parameter validation to `fill_cells()` when converting cells to html

## 0.7.35

Fix syntax for generated HTML tables

## 0.7.34

* Reduce excessive logging

## 0.7.33

* BREAKING CHANGE: removes legacy detectron2 model
* deps: remove layoutparser optional dependencies

## 0.7.32

* refactor: remove all code related to filling inferred elements text from embedded text (pdfminer).
* bug: set the Chipper max_length variable

## 0.7.31

* refactor: remove all `cid` related code that was originally added to filter out invalid `pdfminer` text
* enhancement: Wrapped hf_hub_download with a function that checks for local file before checking HF

## 0.7.30

* fix: table transformer doesn't return multiple cells with same coordinates
*
## 0.7.29

* fix: table transformer predictions are now removed if confidence is below threshold


## 0.7.28

* feat: allow table transformer agent to return table prediction in not parsed format

## 0.7.27

* fix: remove pin from `onnxruntime` dependency.

## 0.7.26

* feat: add a set of new `ElementType`s to extend future element types recognition
* feat: allow registering of new models for inference using `unstructured_inference.models.base.register_new_model` function

## 0.7.25

* fix: replace `Rectangle.is_in()` with `Rectangle.is_almost_subregion_of()` when filling in an inferred element with embedded text
* bug: check for None in Chipper bounding box reduction
* chore: removes `install-detectron2` from the `Makefile`
* fix: convert label_map keys read from os.environment `UNSTRUCTURED_DEFAULT_MODEL_INITIALIZE_PARAMS_JSON_PATH` to int type
* feat: removes supergradients references

## 0.7.24

* fix: assign value to `text_as_html` element attribute only if `text` attribute contains HTML tags.

## 0.7.23

* fix: added handling in `UnstructuredTableTransformerModel` for if `recognize` returns an empty
  list in `run_prediction`.

## 0.7.22

* fix: add logic to handle computation of intersections betwen 2 `Rectangle`s when a `Rectangle` has `None` value in its coordinates

## 0.7.21

* fix: fix a bug where chipper, or any element extraction model based `PageLayout` object, lack `image_metadata` and other attributes that are required for downstream processing; this fix also reduces the memory overhead of using chipper model

## 0.7.20

* chipper-v3: improved table prediction

## 0.7.19

* refactor: remove all OCR related code

## 0.7.18

* refactor: remove all image extraction related code

## 0.7.17

* refactor: remove all `pdfminer` related code
* enhancement: improved Chipper bounding boxes

## 0.7.16

* bug: Allow supplied ONNX models to use label_map dictionary from json file

## 0.7.15

* enhancement: Enable env variables for model definition

## 0.7.14

* enhancement: Remove Super-Gradients Dependency and Allow General Onnx Models Instead

## 0.7.13

* refactor: add a class `ElementType` for the element type constants and use the constants to replace element type strings
* enhancement: support extracting elements with types `Picture` and `Figure`
* fix: update logger in table initalization where the logger info was not showing
* chore: supress UserWarning about specified model providers

## 0.7.12

* change the default model to yolox, as table output appears to be better and speed is similar to `yolox_quantized`

## 0.7.11

* chore: remove logger info for chipper since its private
* fix: update broken slack invite link in chipper logger info
* enhancement: Improve error message when # images extracted doesn't match # page layouts.
* fix: use automatic mixed precision on GPU for Chipper
* fix: chipper Table elements now match other layout models' Table element format: html representation is stored in `text_as_html` attribute and `text` attribute stores text without html tags

## 0.7.10

* Handle kwargs explicitly when needed, suppress otherwise
* fix: Reduce Chipper memory consumption on x86_64 cpus
* fix: Skips ordering elements coming from Chipper
* fix: After refactoring to introduce Chipper, annotate() wasn't able to show text with extra info from elements, this is fixed now.
* feat: add table cell and dataframe output formats to table transformer's `run_prediction` call
* breaking change: function `unstructured_inference.models.tables.recognize` no longer takes `out_html` parameter and it now only returns table cell data format (lists of dictionaries)

## 0.7.9

* Allow table model to accept optional OCR tokens

## 0.7.8

* Fix: include onnx as base dependency.

## 0.7.7

• Fix a memory leak in DonutProcessor when using large images in numpy format
• Set the right settings for beam search size > 1
• Fix a bug that in very rare cases made the last element predicted by Chipper to have a bbox = None

## 0.7.6

* fix a bug where invalid zoom factor lead to exceptions; now invalid zoom factors results in no scaling of the image

## 0.7.5

* Improved packaging

## 0.7.4

* Dynamic beam search size has been implemented for Chipper, the decoding process starts with a size = 1 and changes to size = 3 if repetitions appear.
* Fixed bug when PDFMiner predicts that an image text occupies the full page and removes annotations by Chipper.
* Added random seed to Chipper text generation to avoid differences between calls to Chipper.
* Allows user to use super-gradients model if they have a callback predict function, a yaml file with names field corresponding to classes and a path to the model weights

## 0.7.3

* Integration of Chipperv2 and additional Chipper functionality, which includes automatic detection of GPU,
bounding box prediction and hierarchical representation.
* Remove control characters from the text of all layout elements

## 0.7.2

* Sort elements extracted by `pdfminer` to get consistent result from `aggregate_by_block()`

## 0.7.1

* Download yolox_quantized from HF

## 0.7.0

* Remove all OCR related code expect the table OCR code

## 0.6.6

* Stop passing ocr_languages parameter into paddle to avoid invalid paddle language code error, this will be fixed until
we have the mapping from standard language code to paddle language code.
## 0.6.5

* Add functionality to keep extracted image elements while merging inferred layout with extracted layout
* Fix `source` property for elements generated by pdfminer.
* Add 'OCR-tesseract' and 'OCR-paddle' as sources for elements generated by OCR.

## 0.6.4

* add a function to automatically scale table crop images based on text height so the text height is optimum for `tesseract` OCR task
* add the new image auto scaling parameters to `config.py`

## 0.6.3

* fix a bug where padded table structure bounding boxes are not shifted back into the original image coordinates correctly

## 0.6.2

* move the confidence threshold for table transformer to config

## 0.6.1

* YoloX_quantized is now the default model. This models detects most diverse types and detect tables better than previous model.
* Since detection models tend to nest elements inside others(specifically in Tables), an algorithm has been added for reducing this
  behavior. Now all the elements produced by detection models are disjoint and they don't produce overlapping regions, which helps
  reduce duplicated content.
* Add `source` property to our elements, so you can know where the information was generated (OCR or detection model)

## 0.6.0

* add a config class to handle parameter configurations for inference tasks; parameters in the config class can be set via environement variables
* update behavior of `pad_image_with_background_color` so that input `pad` is applied to all sides

## 0.5.31

* Add functionality to extract and save images from the page
* Add functionality to get only "true" embedded images when extracting elements from PDF pages
* Update the layout visualization script to be able to show only image elements if need
* add an evaluation metric for table comparison based on token similarity
* fix paddle unit tests where `make test` fails since paddle doesn't work on M1/M2 chip locally

## 0.5.28

* add env variable `ENTIRE_PAGE_OCR` to specify using paddle or tesseract on entire page OCR

## 0.5.27

* table structure detection now pads the input image by 25 pixels in all 4 directions to improve its recall

## 0.5.26

* support paddle with both cpu and gpu and assumed it is pre-installed

## 0.5.25

* fix a bug where `cells_to_html` doesn't handle cells spanning multiple rows properly

## 0.5.24

* remove `cv2` preprocessing step before OCR step in table transformer

## 0.5.23

* Add functionality to bring back embedded images in PDF

## 0.5.22

* Add object-detection classification probabilities to LayoutElement for all currently implemented object detection models

## 0.5.21

* adds `safe_division` to replae 0 with machine epsilon for `float` to avoid division by 0
* apply `safe_division` to area overlap calculations in `unstructured_inference/inference/elements.py`

## 0.5.20

* Adds YoloX quantized model

## 0.5.19

* Add functionality to supplement detected layout with elements from the full page OCR
* Add functionality to annotate any layout(extracted, inferred, OCR) on a page

## 0.5.18

* Fix for incorrect type assignation at ingest test

## 0.5.17

* Use `OMP_THREAD_LIMIT` to improve tesseract performance

## 0.5.16

* Fix to no longer create a directory for storing processed images
* Hot-load images for annotation

## 0.5.15

* Handle an uncaught TesseractError

## 0.5.14

* Add TIFF test file and TIFF filetype to `test_from_image_file` in `test_layout`

## 0.5.13

* Fix extracted image elements being included in layout merge

## 0.5.12

* Add multipage TIFF extraction support
* Fix a pdfminer error when using `process_data_with_model`

## 0.5.11

* Add warning when chipper is used with < 300 DPI
* Use None default for dpi so defaults can be properly handled upstream

## 0.5.10

* Implement full-page OCR

## 0.5.9

* Handle exceptions from Tesseract

## 0.5.8

* Add alternative architecture for detectron2 (but default is unchanged)
* Updates:

| Library       | From      | To       |
|---------------|-----------|----------|
| transformers  | 4.29.2    | 4.30.2   |
| opencv-python | 4.7.0.72  | 4.8.0.74 |
| ipython       | 8.12.2    | 8.14.0   |

* Cache named models that have been loaded

## 0.5.7

* hotfix to handle issue storing images in a new dir when the pdf has no file extension

## 0.5.6

* Update the `annotate` and `_get_image_array` methods of `PageLayout` to get the image from the `image_path` property if the `image` property is `None`.
* Add functionality to store pdf images for later use.
* Add `image_metadata` property to `PageLayout` & set `page.image` to None to reduce memory usage.
* Update `DocumentLayout.from_file` to open only one image.
* Update `load_pdf` to return either Image objects or Image paths.
* Warns users that Chipper is a beta model.
* Exposed control over dpi when converting PDF to an image.
* Updated detectron2 version to avoid errors related to deprecated PIL reference

## 0.5.5

* Rename large model to chipper
* Added functionality to write images to computer storage temporarily instead of keeping them in memory for `pdf2image.convert_from_path`
* Added functionality to convert a PDF in small chunks of pages at a time for `pdf2image.convert_from_path`
* Table processing check for the area of the package to fix division by zero bug
* Added CUDA and TensorRT execution providers for yolox and detectron2onnx model.
* Warning for onnx version of detectron2 for empty pages suppresed.

## 0.5.4

* Tweak to element ordering to make it more deterministic

## 0.5.3

* Refactor for large model

## 0.5.2

* Combine inferred elements with extracted elements
* Add ruff to keep code consistent with unstructured
* Configure fallback for OCR token if paddleocr doesn't work to use tesseract

## 0.5.1

* Add annotation for pages
* Store page numbers when processing PDFs
* Hotfix to handle inference of blank pages using ONNX detectron2
* Revert ordering change to investigate examples of misordering

## 0.5.0

* Preserve image format in PIL.Image.Image when loading
* Added ONNX version of Detectron2 and make default model
* Remove API code, we don't serve this as a standalone API any more
* Update ordering logic to account for multicolumn documents.

## 0.4.4

* Fixed patches not being a package.

## 0.4.3

* Patch pdfminer.six to fix parsing bug

## 0.4.2

* Output of table extraction is now stored in `text_as_html` property rather than `text` property

## 0.4.1

* Added the ability to pass `ocr_languages` to the OCR agent for users who need
  non-English language packs.

## 0.4.0

* Added logic to partition granular elements (words, characters) by proximity
* Text extraction is now delegated to text regions rather than being handled centrally
* Fixed embedded image coordinates being interpreted differently than embedded text coordinates
* Update to how dependencies are being handled
* Update detectron2 version

## 0.3.2

* Allow extracting tables from higher level functions

## 0.3.1

* Pin protobuf version to avoid errors
* Make paddleocr an extra again

## 0.3.0

* Fix for text block detection
* Add paddleocr dependency to setup for x86_64 machines

## 0.2.14

* Suppressed processing progress bars

## 0.2.13

* Add table processing
* Change OCR logic to be aware of PDF image elements

## 0.2.12

* Fix for processing RGBA images

## 0.2.11

* Fixed some cases where image elements were not being OCR'd

## 0.2.10

* Removed control characters from tesseract output

## 0.2.9

* Removed multithreading from OCR (DocumentLayout.get_elements_from_layout)

## 0.2.8

* Refactored YoloX inference code to integrate better with framework
* Improved testing time

## 0.2.7

* Fixed duplicated load_pdf call

## 0.2.6

* Add donut model script for image prediction
* Add sample receipt and test for donut prediction

## 0.2.5

* Add YoloX model for images and PDFs
* Add generic model interface

## 0.2.4

* Download default model from huggingface
* Clarify error when trying to open file that doesn't exist as an image

## 0.2.3

* Pins the version of `opencv-python` for linux compatibility

## 0.2.2

* Add capability to process image files
* Add logic to use OCR when layout text is full of unknown characters

## 0.2.1

* Refactor to facilitate local inference
* Removes BasicConfig from logger configuration
* Implement auto model downloading

## 0.2.0

* Initial release of unstructured-inference
