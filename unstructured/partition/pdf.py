import contextlib
import io
import os
import re
import warnings
from tempfile import SpooledTemporaryFile
from typing import IO, Any, BinaryIO, Iterator, List, Optional, Sequence, Tuple, Union, cast

import numpy as np
import pdf2image
import PIL
from pdfminer.converter import PDFPageAggregator, PDFResourceManager
from pdfminer.layout import (
    LAParams,
    LTChar,
    LTContainer,
    LTImage,
    LTItem,
    LTTextBox,
)
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import open_filename

from unstructured.chunking.title import add_chunking_strategy
from unstructured.cleaners.core import (
    clean_extra_whitespace_with_index_run,
    index_adjustment_after_clean_extra_whitespace,
)
from unstructured.documents.coordinates import PixelSpace, PointSpace
from unstructured.documents.elements import (
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    Image,
    Link,
    ListItem,
    PageBreak,
    Text,
    process_metadata,
)
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
)
from unstructured.logger import logger, trace_logger
from unstructured.nlp.patterns import PARAGRAPH_PATTERN
from unstructured.partition.common import (
    convert_to_bytes,
    document_to_element_list,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
    spooled_to_bytes_io_if_needed,
)
from unstructured.partition.lang import (
    convert_old_ocr_languages_to_languages,
    prepare_languages_for_tesseract,
)
from unstructured.partition.strategies import determine_pdf_or_image_strategy
from unstructured.partition.text import element_from_text, partition_text
from unstructured.partition.utils.constants import (
    SORT_MODE_BASIC,
    SORT_MODE_DONT,
    SORT_MODE_XY_CUT,
    OCRMode,
)
from unstructured.partition.utils.sorting import (
    coord_has_valid_points,
    sort_page_elements,
)
from unstructured.utils import requires_dependencies

RE_MULTISPACE_INCLUDING_NEWLINES = re.compile(pattern=r"\s+", flags=re.DOTALL)


def default_hi_res_model() -> str:
    # a light config for the hi res model; this is not defined as a constant so that no setting of
    # the default hi res model name is done on importing of this submodule; this allows (if user
    # prefers) for setting env after importing the sub module and changing the default model name
    return os.environ.get("UNSTRUCTURED_HI_RES_MODEL_NAME", "yolox_quantized")


@process_metadata()
@add_metadata_with_filetype(FileType.PDF)
@add_chunking_strategy()
def partition_pdf(
    filename: str = "",
    file: Optional[Union[BinaryIO, SpooledTemporaryFile]] = None,
    include_page_breaks: bool = False,
    strategy: str = "auto",
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,  # changing to optional for deprecation
    languages: List[str] = ["eng"],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    chunking_strategy: Optional[str] = None,
    links: Sequence[Link] = [],
    **kwargs,
) -> List[Element]:
    """Parses a pdf document into a list of interpreted elements.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    strategy
        The strategy to use for partitioning the PDF. Valid strategies are "hi_res",
        "ocr_only", and "fast". When using the "hi_res" strategy, the function uses
        a layout detection model to identify document elements. When using the
        "ocr_only" strategy, partition_pdf simply extracts the text from the
        document using OCR and processes it. If the "fast" strategy is used, the text
        is extracted directly from the PDF. The default strategy `auto` will determine
        when a page can be extracted using `fast` mode, otherwise it will fall back to `hi_res`.
    infer_table_structure
        Only applicable if `strategy=hi_res`.
        If True, any Table elements that are extracted will also have a metadata field
        named "text_as_html" where the table's text content is rendered into an html string.
        I.e., rows and cells are preserved.
        Whether True or False, the "text" field is always present in any Table element
        and is the text content of the table (no structure).
    languages
        The languages present in the document, for use in partitioning and/or OCR. To use a language
        with Tesseract, you'll first need to install the appropriate Tesseract language pack.
    max_partition
        The maximum number of characters to include in a partition. If None is passed,
        no maximum is applied. Only applies to the "ocr_only" strategy.
    min_partition
        The minimum number of characters to include in a partition. Only applies if
        processing text/plain content.
    metadata_last_modified
        The last modified date for the document.
    """
    exactly_one(filename=filename, file=file)

    if ocr_languages is not None:
        # check if languages was set to anything not the default value
        # languages and ocr_languages were therefore both provided - raise error
        if languages != ["eng"]:
            raise ValueError(
                "Only one of languages and ocr_languages should be specified. "
                "languages is preferred. ocr_languages is marked for deprecation.",
            )

        else:
            languages = convert_old_ocr_languages_to_languages(ocr_languages)
            logger.warning(
                "The ocr_languages kwarg will be deprecated in a future version of unstructured. "
                "Please use languages instead.",
            )

    return partition_pdf_or_image(
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        strategy=strategy,
        infer_table_structure=infer_table_structure,
        languages=languages,
        max_partition=max_partition,
        min_partition=min_partition,
        metadata_last_modified=metadata_last_modified,
        **kwargs,
    )


def extractable_elements(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    include_page_breaks: bool = False,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
):
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    return _partition_pdf_with_pdfminer(
        filename=filename,
        file=file,
        include_page_breaks=include_page_breaks,
        metadata_last_modified=metadata_last_modified,
        **kwargs,
    )


def get_the_last_modification_date_pdf_or_img(
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    filename: Optional[str] = "",
) -> Union[str, None]:
    last_modification_date = None
    if not file and filename:
        last_modification_date = get_last_modified_date(filename=filename)
    elif not filename and file:
        last_modification_date = get_last_modified_date_from_file(file=file)
    return last_modification_date


def partition_pdf_or_image(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    is_image: bool = False,
    include_page_breaks: bool = False,
    strategy: str = "auto",
    infer_table_structure: bool = False,
    ocr_languages: Optional[str] = None,
    languages: Optional[List[str]] = ["eng"],
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    metadata_last_modified: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Parses a pdf or image document into a list of interpreted elements."""
    # TODO(alan): Extract information about the filetype to be processed from the template
    # route. Decoding the routing should probably be handled by a single function designed for
    # that task so as routing design changes, those changes are implemented in a single
    # function.

    # The auto `partition` function uses `None` as a default because the default for
    # `partition_pdf` and `partition_img` conflict with the other partitioners that use ["auto"]
    if languages is None:
        languages = ["eng"]

    if not isinstance(languages, list):
        raise TypeError(
            "The language parameter must be a list of language codes as strings, ex. ['eng']",
        )

    if ocr_languages is not None:
        if languages != ["eng"]:
            raise ValueError(
                "Only one of languages and ocr_languages should be specified. "
                "languages is preferred. ocr_languages is marked for deprecation.",
            )

        else:
            languages = convert_old_ocr_languages_to_languages(ocr_languages)
            logger.warning(
                "The ocr_languages kwarg will be deprecated in a future version of unstructured. "
                "Please use languages instead.",
            )

    last_modification_date = get_the_last_modification_date_pdf_or_img(
        file=file,
        filename=filename,
    )

    if (
        not is_image
        and determine_pdf_or_image_strategy(
            strategy,
            filename=filename,
            file=file,
            is_image=is_image,
            infer_table_structure=infer_table_structure,
        )
        != "ocr_only"
    ):
        extracted_elements = extractable_elements(
            filename=filename,
            file=spooled_to_bytes_io_if_needed(file),
            include_page_breaks=include_page_breaks,
            metadata_last_modified=metadata_last_modified or last_modification_date,
            **kwargs,
        )
        pdf_text_extractable = any(
            isinstance(el, Text) and el.text.strip() for el in extracted_elements
        )
    else:
        pdf_text_extractable = False

    strategy = determine_pdf_or_image_strategy(
        strategy,
        filename=filename,
        file=file,
        is_image=is_image,
        infer_table_structure=infer_table_structure,
        pdf_text_extractable=pdf_text_extractable,
    )

    if strategy == "hi_res":
        # NOTE(robinson): Catches a UserWarning that occurs when detectron is called
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _layout_elements = _partition_pdf_or_image_local(
                filename=filename,
                file=spooled_to_bytes_io_if_needed(file),
                is_image=is_image,
                infer_table_structure=infer_table_structure,
                include_page_breaks=include_page_breaks,
                languages=languages,
                metadata_last_modified=metadata_last_modified or last_modification_date,
                **kwargs,
            )
            layout_elements = []
            for el in _layout_elements:
                if hasattr(el, "category") and el.category == "UncategorizedText":
                    new_el = element_from_text(cast(Text, el).text)
                    new_el.metadata = el.metadata
                else:
                    new_el = el
                layout_elements.append(new_el)

    elif strategy == "fast":
        return extracted_elements

    elif strategy == "ocr_only":
        # NOTE(robinson): Catches file conversion warnings when running with PDFs
        with warnings.catch_warnings():
            return _partition_pdf_or_image_with_ocr(
                filename=filename,
                file=file,
                include_page_breaks=include_page_breaks,
                languages=languages,
                is_image=is_image,
                max_partition=max_partition,
                min_partition=min_partition,
                metadata_last_modified=metadata_last_modified or last_modification_date,
            )

    return layout_elements


@requires_dependencies("unstructured_inference")
def _partition_pdf_or_image_local(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO]] = None,
    is_image: bool = False,
    infer_table_structure: bool = False,
    include_page_breaks: bool = False,
    languages: Optional[List[str]] = ["eng"],
    ocr_mode: str = OCRMode.FULL_PAGE.value,
    model_name: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    **kwargs,
) -> List[Element]:
    """Partition using package installed locally."""
    from unstructured_inference.inference.layout import (
        process_data_with_model,
        process_file_with_model,
    )

    from unstructured.partition.ocr import (
        process_data_with_ocr,
        process_file_with_ocr,
    )

    ocr_languages = prepare_languages_for_tesseract(languages)

    model_name = model_name or default_hi_res_model()
    pdf_image_dpi = kwargs.pop("pdf_image_dpi", None)
    if pdf_image_dpi is None:
        pdf_image_dpi = 300 if model_name == "chipper" else 200
    if (pdf_image_dpi < 300) and (model_name == "chipper"):
        logger.warning(
            "The Chipper model performs better when images are rendered with DPI >= 300 "
            f"(currently {pdf_image_dpi}).",
        )

    # NOTE(christine): Need to extract images from PDF's
    extract_images_in_pdf = kwargs.get("extract_images_in_pdf", False)
    image_output_dir_path = kwargs.get("image_output_dir_path", None)
    process_with_model_extra_kwargs = {
        "extract_images_in_pdf": extract_images_in_pdf,
        "image_output_dir_path": image_output_dir_path,
    }

    process_with_model_kwargs = {}
    for key, value in process_with_model_extra_kwargs.items():
        if value:
            process_with_model_kwargs[key] = value

    if file is None:
        # NOTE(christine): out_layout = extracted_layout + inferred_layout
        out_layout = process_file_with_model(
            filename,
            is_image=is_image,
            extract_tables=infer_table_structure,
            model_name=model_name,
            pdf_image_dpi=pdf_image_dpi,
            **process_with_model_kwargs,
        )
        if model_name.startswith("chipper"):
            # NOTE(alan): We shouldn't do OCR with chipper
            final_layout = out_layout
        else:
            final_layout = process_file_with_ocr(
                filename,
                out_layout,
                is_image=is_image,
                ocr_languages=ocr_languages,
                ocr_mode=ocr_mode,
                pdf_image_dpi=pdf_image_dpi,
            )
    else:
        out_layout = process_data_with_model(
            file,
            is_image=is_image,
            extract_tables=infer_table_structure,
            model_name=model_name,
            pdf_image_dpi=pdf_image_dpi,
            **process_with_model_kwargs,
        )
        if model_name.startswith("chipper"):
            # NOTE(alan): We shouldn't do OCR with chipper
            final_layout = out_layout
        else:
            if hasattr(file, "seek"):
                file.seek(0)
            final_layout = process_data_with_ocr(
                file,
                out_layout,
                is_image=is_image,
                ocr_languages=ocr_languages,
                ocr_mode=ocr_mode,
                pdf_image_dpi=pdf_image_dpi,
            )

    # NOTE(alan): starting with v2, chipper sorts the elements itself.
    if model_name == "chipper":
        kwargs["sort_mode"] = SORT_MODE_DONT

    elements = document_to_element_list(
        final_layout,
        sortable=True,
        include_page_breaks=include_page_breaks,
        last_modification_date=metadata_last_modified,
        # NOTE(crag): do not attempt to derive ListItem's from a layout-recognized "List"
        # block with NLP rules. Otherwise, the assumptions in
        # unstructured.partition.common::layout_list_to_list_items often result in weird chunking.
        infer_list_items=False,
        detection_origin="image" if is_image else "pdf",
        **kwargs,
    )

    out_elements = []
    for el in elements:
        if isinstance(el, PageBreak) and not include_page_breaks:
            continue

        if isinstance(el, Image):
            # NOTE(crag): small chunks of text from Image elements tend to be garbage
            if not el.metadata.image_path and (
                el.text is None or len(el.text) < 24 or el.text.find(" ") == -1
            ):
                continue
            else:
                out_elements.append(cast(Element, el))
        # NOTE(crag): this is probably always a Text object, but check for the sake of typing
        elif isinstance(el, Text):
            el.text = re.sub(
                RE_MULTISPACE_INCLUDING_NEWLINES,
                " ",
                el.text or "",
            ).strip()
            # NOTE(alan): with chipper there are parent elements with no text we don't want to
            # filter those out and leave the children orphaned.
            if el.text or isinstance(el, PageBreak) or model_name.startswith("chipper"):
                out_elements.append(cast(Element, el))

    return out_elements


@requires_dependencies("pdfminer", "local-inference")
def _partition_pdf_with_pdfminer(
    filename: str = "",
    file: Optional[IO[bytes]] = None,
    include_page_breaks: bool = False,
    metadata_last_modified: Optional[str] = None,
    **kwargs: Any,
) -> List[Element]:
    """Partitions a PDF using PDFMiner instead of using a layoutmodel. Used for faster
    processing or detectron2 is not available.

    Implementation is based on the `extract_text` implemenation in pdfminer.six, but
    modified to support tracking page numbers and working with file-like objects.

    ref: https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/high_level.py
    """
    exactly_one(filename=filename, file=file)
    if filename:
        with open_filename(filename, "rb") as fp:
            fp = cast(BinaryIO, fp)
            elements = _process_pdfminer_pages(
                fp=fp,
                filename=filename,
                include_page_breaks=include_page_breaks,
                metadata_last_modified=metadata_last_modified,
                **kwargs,
            )

    elif file:
        fp = cast(BinaryIO, file)
        elements = _process_pdfminer_pages(
            fp=fp,
            filename=filename,
            include_page_breaks=include_page_breaks,
            metadata_last_modified=metadata_last_modified,
            **kwargs,
        )

    return elements


def _extract_text(item: LTItem) -> str:
    """Recursively extracts text from PDFMiner objects to account
    for scenarios where the text is in a sub-container."""
    if hasattr(item, "get_text"):
        return item.get_text()

    elif isinstance(item, LTContainer):
        text = ""
        for child in item:
            text += _extract_text(child) or ""
        return text

    elif isinstance(item, (LTTextBox, LTImage)):
        # TODO(robinson) - Support pulling text out of images
        # https://github.com/pdfminer/pdfminer.six/blob/master/pdfminer/image.py#L90
        return "\n"
    return "\n"


def _process_pdfminer_pages(
    fp: BinaryIO,
    filename: str = "",
    include_page_breaks: bool = False,
    metadata_last_modified: Optional[str] = None,
    **kwargs,
):
    """Uses PDF miner to split a document into pages and process them."""
    elements: List[Element] = []
    sort_mode = kwargs.get("sort_mode", SORT_MODE_XY_CUT)

    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for i, page in enumerate(PDFPage.get_pages(fp)):  # type: ignore
        interpreter.process_page(page)
        page_layout = device.get_result()

        width, height = page_layout.width, page_layout.height

        page_elements = []
        annotation_list = []

        coordinate_system = PixelSpace(
            width=width,
            height=height,
        )
        if page.annots:
            annotation_list = get_uris(page.annots, height, coordinate_system, i + 1)

        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)
            bbox = (x1, y1, x2, y2)

            urls_metadata = []

            if len(annotation_list) > 0 and isinstance(obj, LTTextBox):
                annotations_within_element = check_annotations_within_element(
                    annotation_list,
                    bbox,
                    i + 1,
                )
                _, words = get_word_bounding_box_from_element(obj, height)
                for annot in annotations_within_element:
                    urls_metadata.append(map_bbox_and_index(words, annot))

            if hasattr(obj, "get_text"):
                _text_snippets = [obj.get_text()]
            else:
                _text = _extract_text(obj)
                _text_snippets = re.split(PARAGRAPH_PATTERN, _text)

            for _text in _text_snippets:
                _text, moved_indices = clean_extra_whitespace_with_index_run(_text)
                if _text.strip():
                    points = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
                    element = element_from_text(
                        _text,
                        coordinates=points,
                        coordinate_system=coordinate_system,
                    )
                    coordinates_metadata = CoordinatesMetadata(
                        points=points,
                        system=coordinate_system,
                    )

                    links: List[Link] = []
                    for url in urls_metadata:
                        with contextlib.suppress(IndexError):
                            links.append(
                                {
                                    "text": url["text"],
                                    "url": url["uri"],
                                    "start_index": index_adjustment_after_clean_extra_whitespace(
                                        url["start_index"],
                                        moved_indices,
                                    ),
                                },
                            )

                    element.metadata = ElementMetadata(
                        filename=filename,
                        page_number=i + 1,
                        coordinates=coordinates_metadata,
                        last_modified=metadata_last_modified,
                        links=links,
                    )
                    element.metadata.detection_origin = "pdfminer"
                    page_elements.append(element)
        list_item = 0
        updated_page_elements = []  # type: ignore
        coordinate_system = PixelSpace(width=width, height=height)
        for page_element in page_elements:
            if isinstance(page_element, ListItem):
                list_item += 1
                list_page_element = page_element
                list_item_text = page_element.text
                list_item_coords = page_element.metadata.coordinates
            elif list_item > 0 and check_coords_within_boundary(
                page_element.metadata.coordinates,
                list_item_coords,
            ):
                text = page_element.text  # type: ignore
                list_item_text = list_item_text + " " + text
                x1 = min(
                    list_page_element.metadata.coordinates.points[0][0],
                    page_element.metadata.coordinates.points[0][0],
                )
                x2 = max(
                    list_page_element.metadata.coordinates.points[2][0],
                    page_element.metadata.coordinates.points[2][0],
                )
                y1 = min(
                    list_page_element.metadata.coordinates.points[0][1],
                    page_element.metadata.coordinates.points[0][1],
                )
                y2 = max(
                    list_page_element.metadata.coordinates.points[1][1],
                    page_element.metadata.coordinates.points[1][1],
                )
                points = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))
                list_page_element.text = list_item_text
                list_page_element.metadata.coordinates = CoordinatesMetadata(
                    points=points,
                    system=coordinate_system,
                )
                page_element = list_page_element
                updated_page_elements.pop()

            updated_page_elements.append(page_element)

        page_elements = updated_page_elements
        del updated_page_elements

        # NOTE(crag, christine): always do the basic sort first for determinsitic order across
        # python versions.
        sorted_page_elements = sort_page_elements(page_elements, SORT_MODE_BASIC)
        if sort_mode != SORT_MODE_BASIC:
            sorted_page_elements = sort_page_elements(sorted_page_elements, sort_mode)

        elements += sorted_page_elements

        if include_page_breaks:
            elements.append(PageBreak(text=""))

    return elements


def convert_pdf_to_images(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    chunk_size: int = 10,
) -> Iterator[PIL.Image.Image]:
    # Convert a PDF in small chunks of pages at a time (e.g. 1-10, 11-20... and so on)
    exactly_one(filename=filename, file=file)
    if file is not None:
        f_bytes = convert_to_bytes(file)
        info = pdf2image.pdfinfo_from_bytes(f_bytes)
    else:
        f_bytes = None
        info = pdf2image.pdfinfo_from_path(filename)

    total_pages = info["Pages"]
    for start_page in range(1, total_pages + 1, chunk_size):
        end_page = min(start_page + chunk_size - 1, total_pages)
        if f_bytes is not None:
            chunk_images = pdf2image.convert_from_bytes(
                f_bytes,
                first_page=start_page,
                last_page=end_page,
            )
        else:
            chunk_images = pdf2image.convert_from_path(
                filename,
                first_page=start_page,
                last_page=end_page,
            )

        for image in chunk_images:
            yield image


def _get_element_box(
    boxes: List[str],
    char_count: int,
) -> Tuple[Tuple[Tuple[float, float], Tuple[float, int], Tuple[int, int], Tuple[int, float]], int]:
    """Helper function to get the bounding box of an element.

    Args:
        boxes (List[str])
        char_count (int)
    """
    min_x = float("inf")
    min_y = float("inf")
    max_x = 0
    max_y = 0
    for box in boxes:
        _, _x1, _y1, _x2, _y2, _ = box.split()

        x1, y1, x2, y2 = map(int, [_x1, _y1, _x2, _y2])
        min_x = min(min_x, x1)
        min_y = min(min_y, y1)
        max_x = max(max_x, x2)
        max_y = max(max_y, y2)

    return ((min_x, min_y), (min_x, max_y), (max_x, max_y), (max_x, min_y)), char_count


def _add_pytesseract_bboxes_to_elements(
    elements: List[Text],
    bboxes_string: str,
    width: int,
    height: int,
) -> List[Text]:
    """
    Get the bounding box of each element and add it to element.metadata.coordinates

    Args:
        elements: elements containing text detected by pytesseract.image_to_string.
        bboxes_string (str): The return value of pytesseract.image_to_boxes.
        width: width of image
        height: height of image
    """
    # (NOTE) jennings: This function was written with pytesseract in mind, but
    # paddle returns similar values via `ocr.ocr(img)`.
    # See more at issue #1176: https://github.com/Unstructured-IO/unstructured/issues/1176
    point_space = PointSpace(
        width=width,
        height=height,
    )
    pixel_space = PixelSpace(
        width=width,
        height=height,
    )

    boxes = bboxes_string.strip().split("\n")
    box_idx = 0
    for element in elements:
        if not element.text:
            box_idx += 1
            continue
        try:
            while boxes[box_idx][0] != element.text[0]:
                box_idx += 1
        except IndexError:
            break
        char_count = len(element.text.replace(" ", ""))
        if box_idx + char_count > len(boxes):
            break
        _points, char_count = _get_element_box(
            boxes=boxes[box_idx : box_idx + char_count],  # noqa
            char_count=char_count,
        )
        box_idx += char_count

        converted_points = point_space.convert_multiple_coordinates_to_new_system(
            pixel_space,
            _points,
        )

        element.metadata.coordinates = CoordinatesMetadata(
            points=converted_points,
            system=pixel_space,
        )
    return elements


@requires_dependencies("unstructured_pytesseract")
def _partition_pdf_or_image_with_ocr(
    filename: str = "",
    file: Optional[Union[bytes, IO[bytes]]] = None,
    include_page_breaks: bool = False,
    languages: Optional[List[str]] = ["eng"],
    is_image: bool = False,
    max_partition: Optional[int] = 1500,
    min_partition: Optional[int] = 0,
    metadata_last_modified: Optional[str] = None,
):
    """Partitions an image or PDF using Tesseract OCR. For PDFs, each page is converted
    to an image prior to processing."""
    import unstructured_pytesseract

    ocr_languages = prepare_languages_for_tesseract(languages)

    if is_image:
        if file is not None:
            image = PIL.Image.open(file)
            text, _bboxes = unstructured_pytesseract.run_and_get_multiple_output(
                np.array(image),
                extensions=["txt", "box"],
                lang=ocr_languages,
            )
        else:
            image = PIL.Image.open(filename)
            text, _bboxes = unstructured_pytesseract.run_and_get_multiple_output(
                np.array(image),
                extensions=["txt", "box"],
                lang=ocr_languages,
            )
        elements = partition_text(
            text=text,
            max_partition=max_partition,
            min_partition=min_partition,
            metadata_last_modified=metadata_last_modified,
            detection_origin="OCR",
        )
        width, height = image.size
        _add_pytesseract_bboxes_to_elements(
            elements=cast(List[Text], elements),
            bboxes_string=_bboxes,
            width=width,
            height=height,
        )

    else:
        elements = []
        page_number = 0
        for image in convert_pdf_to_images(filename, file):
            page_number += 1
            metadata = ElementMetadata(
                filename=filename,
                page_number=page_number,
                last_modified=metadata_last_modified,
                languages=languages,
            )
            metadata.detection_origin = "OCR"
            _text, _bboxes = unstructured_pytesseract.run_and_get_multiple_output(
                image,
                extensions=["txt", "box"],
                lang=ocr_languages,
            )
            width, height = image.size

            _elements = partition_text(
                text=_text,
                max_partition=max_partition,
                min_partition=min_partition,
            )

            for element in _elements:
                element.metadata = metadata

            _add_pytesseract_bboxes_to_elements(
                elements=cast(List[Text], _elements),
                bboxes_string=_bboxes,
                width=width,
                height=height,
            )

            elements.extend(_elements)
            if include_page_breaks:
                elements.append(PageBreak(text=""))
    return elements


def check_coords_within_boundary(
    coordinates: CoordinatesMetadata,
    boundary: CoordinatesMetadata,
    horizontal_threshold: float = 0.2,
    vertical_threshold: float = 0.3,
) -> bool:
    """Checks if the coordinates are within boundary thresholds.
    Parameters
    ----------
    coordinates
        a CoordinatesMetadata input
    boundary
        a CoordinatesMetadata to compare against
    vertical_threshold
        a float ranges from [0,1] to scale the vertical (y-axis) boundary
    horizontal_threshold
        a float ranges from [0,1] to scale the horizontal (x-axis) boundary
    """
    if not coord_has_valid_points(coordinates) and not coord_has_valid_points(boundary):
        trace_logger.detail(  # type: ignore
            f"coordinates {coordinates} and boundary {boundary} did not pass validation",
        )
        return False

    boundary_x_min = boundary.points[0][0]
    boundary_x_max = boundary.points[2][0]
    boundary_y_min = boundary.points[0][1]
    boundary_y_max = boundary.points[1][1]

    line_width = boundary_x_max - boundary_x_min
    line_height = boundary_y_max - boundary_y_min

    x_within_boundary = (
        (coordinates.points[0][0] > boundary_x_min - (horizontal_threshold * line_width))
        and (coordinates.points[2][0] < boundary_x_max + (horizontal_threshold * line_width))
        and (coordinates.points[0][0] >= boundary_x_min)
    )
    y_within_boundary = (
        coordinates.points[0][1] < boundary_y_max + (vertical_threshold * line_height)
    ) and (coordinates.points[0][1] > boundary_y_min - (vertical_threshold * line_height))

    return x_within_boundary and y_within_boundary


def get_uris(
    annots: Union[PDFObjRef, List[PDFObjRef]],
    height: float,
    coordinate_system: Union[PixelSpace, PointSpace],
    page_number: int,
) -> List[dict]:
    """
    Extracts URI annotations from a single or a list of PDF object references on a specific page.
    The type of annots (list or not) depends on the pdf formatting. The function detectes the type
    of annots and then pass on to get_uris_from_annots function as a List.

    Args:
        annots (Union[PDFObjRef, List[PDFObjRef]]): A single or a list of PDF object references
            representing annotations on the page.
        height (float): The height of the page in the specified coordinate system.
        coordinate_system (Union[PixelSpace, PointSpace]): The coordinate system used to represent
            the annotations' coordinates.
        page_number (int): The page number from which to extract annotations.

    Returns:
        List[dict]: A list of dictionaries, each containing information about a URI annotation,
        including its coordinates, bounding box, type, URI link, and page number.
    """
    if isinstance(annots, List):
        return get_uris_from_annots(annots, height, coordinate_system, page_number)
    return get_uris_from_annots(annots.resolve(), height, coordinate_system, page_number)


def get_uris_from_annots(
    annots: List[PDFObjRef],
    height: Union[int, float],
    coordinate_system: Union[PixelSpace, PointSpace],
    page_number: int,
) -> List[dict]:
    """
    Extracts URI annotations from a list of PDF object references.

    Args:
        annots (List[PDFObjRef]): A list of PDF object references representing annotations on
            a page.
        height (Union[int, float]): The height of the page in the specified coordinate system.
        coordinate_system (Union[PixelSpace, PointSpace]): The coordinate system used to represent
            the annotations' coordinates.
        page_number (int): The page number from which to extract annotations.

    Returns:
        List[dict]: A list of dictionaries, each containing information about a URI annotation,
        including its coordinates, bounding box, type, URI link, and page number.
    """
    annotation_list = []
    for annotation in annots:
        annotation_dict = try_resolve(annotation)
        if str(annotation_dict["Subtype"]) != "/'Link'" or "A" not in annotation_dict:
            continue
        x1, y1, x2, y2 = rect_to_bbox(annotation_dict["Rect"], height)
        uri_dict = try_resolve(annotation_dict["A"])
        uri_type = str(uri_dict["S"])

        uri = None
        try:
            if uri_type == "/'URI'":
                uri = try_resolve(try_resolve(uri_dict["URI"])).decode("utf-8")
            if uri_type == "/'GoTo'":
                uri = try_resolve(try_resolve(uri_dict["D"])).decode("utf-8")
        except Exception:
            pass

        points = ((x1, y1), (x1, y2), (x2, y2), (x2, y1))

        coordinates_metadata = CoordinatesMetadata(
            points=points,
            system=coordinate_system,
        )

        annotation_list.append(
            {
                "coordinates": coordinates_metadata,
                "bbox": (x1, y1, x2, y2),
                "type": uri_type,
                "uri": uri,
                "page_number": page_number,
            },
        )
    return annotation_list


def try_resolve(annot: PDFObjRef):
    """
    Attempt to resolve a PDF object reference. If successful, returns the resolved object;
    otherwise, returns the original reference.
    """
    try:
        return annot.resolve()
    except Exception:
        return annot


def rect_to_bbox(
    rect: Tuple[float, float, float, float],
    height: float,
) -> Tuple[float, float, float, float]:
    """
    Converts a PDF rectangle coordinates (x1, y1, x2, y2) to a bounding box in the specified
    coordinate system where the vertical axis is measured from the top of the page.

    Args:
        rect (Tuple[float, float, float, float]): A tuple representing a PDF rectangle
            coordinates (x1, y1, x2, y2).
        height (float): The height of the page in the specified coordinate system.

    Returns:
        Tuple[float, float, float, float]: A tuple representing the bounding box coordinates
        (x1, y1, x2, y2) with the y-coordinates adjusted to be measured from the top of the page.
    """
    x1, y2, x2, y1 = rect
    y1 = height - y1
    y2 = height - y2
    return (x1, y1, x2, y2)


def calculate_intersection_area(
    bbox1: Tuple[float, float, float, float],
    bbox2: Tuple[float, float, float, float],
) -> float:
    """
    Calculate the area of intersection between two bounding boxes.

    Args:
        bbox1 (Tuple[float, float, float, float]): The coordinates of the first bounding box
            in the format (x1, y1, x2, y2).
        bbox2 (Tuple[float, float, float, float]): The coordinates of the second bounding box
            in the format (x1, y1, x2, y2).

    Returns:
        float: The area of intersection between the two bounding boxes. If there is no
        intersection, the function returns 0.0.
    """
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    x_intersection = max(x1_1, x1_2)
    y_intersection = max(y1_1, y1_2)
    x2_intersection = min(x2_1, x2_2)
    y2_intersection = min(y2_1, y2_2)

    if x_intersection < x2_intersection and y_intersection < y2_intersection:
        intersection_area = calculate_bbox_area(
            (x_intersection, y_intersection, x2_intersection, y2_intersection),
        )
        return intersection_area
    else:
        return 0.0


def calculate_bbox_area(bbox: Tuple[float, float, float, float]) -> float:
    """
    Calculate the area of a bounding box.

    Args:
        bbox (Tuple[float, float, float, float]): The coordinates of the bounding box
            in the format (x1, y1, x2, y2).

    Returns:
        float: The area of the bounding box, computed as the product of its width and height.
    """
    x1, y1, x2, y2 = bbox
    area = (x2 - x1) * (y2 - y1)
    return area


def check_annotations_within_element(
    annotation_list: List[dict],
    element_bbox: Tuple[float, float, float, float],
    page_number: int,
    threshold: float = 0.9,
) -> List[dict]:
    """
    Filter annotations that are within or highly overlap with a specified element on a page.

    Args:
        annotation_list (List[dict]): A list of dictionaries, each containing information
            about an annotation.
        element_bbox (Tuple[float, float, float, float]): The bounding box coordinates of the
            specified element in the bbox format (x1, y1, x2, y2).
        page_number (int): The page number to which the annotations and element belong.
        threshold (float, optional): The threshold value (between 0.0 and 1.0) that determines
            the minimum overlap required for an annotation to be considered within the element.
            Default is 0.9.

    Returns:
        List[dict]: A list of dictionaries containing information about annotations that are
        within or highly overlap with the specified element on the given page, based on the
        specified threshold.
    """
    annotations_within_element = []
    for annotation in annotation_list:
        if annotation["page_number"] == page_number:
            annotation_bbox_size = calculate_bbox_area(annotation["bbox"])
            if annotation_bbox_size and (
                calculate_intersection_area(element_bbox, annotation["bbox"]) / annotation_bbox_size
                > threshold
            ):
                annotations_within_element.append(annotation)
    return annotations_within_element


def get_word_bounding_box_from_element(
    obj: LTTextBox,
    height: float,
) -> Tuple[List[LTChar], List[dict]]:
    """
    Extracts characters and word bounding boxes from a PDF text element.

    Args:
        obj (LTTextBox): The PDF text element from which to extract characters and words.
        height (float): The height of the page in the specified coordinate system.

    Returns:
        Tuple[List[LTChar], List[dict]]: A tuple containing two lists:
            - List[LTChar]: A list of LTChar objects representing individual characters.
            - List[dict]: A list of dictionaries, each containing information about a word,
              including its text, bounding box, and start index in the element's text.
    """
    characters = []
    words = []
    text_len = 0

    for text_line in obj:
        word = ""
        x1, y1, x2, y2 = None, None, None, None
        start_index = 0
        for index, character in enumerate(text_line):
            if isinstance(character, LTChar):
                characters.append(character)
                char = character.get_text()

                if word and not char.strip():
                    words.append(
                        {"text": word, "bbox": (x1, y1, x2, y2), "start_index": start_index},
                    )
                    word = ""
                    continue

                # TODO(klaijan) - isalnum() only works with A-Z, a-z and 0-9
                # will need to switch to some pattern matching once we support more languages
                if not word:
                    isalnum = char.isalnum()
                if word and char.isalnum() != isalnum:
                    isalnum = char.isalnum()
                    words.append(
                        {"text": word, "bbox": (x1, y1, x2, y2), "start_index": start_index},
                    )
                    word = ""

                if len(word) == 0:
                    start_index = text_len + index
                    x1 = character.x0
                    y2 = height - character.y0
                    x2 = character.x1
                    y1 = height - character.y1
                else:
                    x2 = character.x1
                    y2 = height - character.y0

                word += char
        text_len += len(text_line)
    return characters, words


def map_bbox_and_index(words: List[dict], annot: dict):
    """
    Maps a bounding box annotation to the corresponding text and start index within a list of words.

    Args:
        words (List[dict]): A list of dictionaries, each containing information about a word,
            including its text, bounding box, and start index.
        annot (dict): The annotation dictionary to be mapped, which will be updated with "text" and
            "start_index" fields.

    Returns:
        dict: The updated annotation dictionary with "text" representing the mapped text and
            "start_index" representing the start index of the mapped text in the list of words.
    """
    if len(words) == 0:
        annot["text"] = ""
        annot["start_index"] = -1
        return annot
    distance_from_bbox_start = np.sqrt(
        (annot["bbox"][0] - np.array([word["bbox"][0] for word in words])) ** 2
        + (annot["bbox"][1] - np.array([word["bbox"][1] for word in words])) ** 2,
    )
    distance_from_bbox_end = np.sqrt(
        (annot["bbox"][2] - np.array([word["bbox"][2] for word in words])) ** 2
        + (annot["bbox"][3] - np.array([word["bbox"][3] for word in words])) ** 2,
    )
    closest_start = try_argmin(distance_from_bbox_start)
    closest_end = try_argmin(distance_from_bbox_end)

    # NOTE(klaijan) - get the word from closest start only if the end index comes after start index
    text = ""
    if closest_end >= closest_start:
        for _ in range(closest_start, closest_end + 1):
            text += " "
            text += words[_]["text"]
    else:
        text = words[closest_start]["text"]

    annot["text"] = text.strip()
    annot["start_index"] = words[closest_start]["start_index"]
    return annot


def try_argmin(array: np.ndarray) -> int:
    """
    Attempt to find the index of the minimum value in a NumPy array.

    Args:
        array (np.ndarray): The NumPy array in which to find the minimum value's index.

    Returns:
        int: The index of the minimum value in the array. If the array is empty or an
        IndexError occurs, it returns -1.
    """
    try:
        return int(np.argmin(array))
    except IndexError:
        return -1
