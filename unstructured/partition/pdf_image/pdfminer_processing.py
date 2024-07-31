from typing import TYPE_CHECKING, BinaryIO, List, Optional, Union, cast

from pdfminer.utils import open_filename

from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image.pdf_image_utils import remove_control_characters
from unstructured.partition.pdf_image.pdfminer_utils import (
    extract_image_objects,
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import SORT_MODE_BASIC, Source
from unstructured.partition.utils.sorting import sort_text_regions
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layout import DocumentLayout


def process_file_with_pdfminer(
    filename: str = "",
    dpi: int = 200,
) -> List[List["TextRegion"]]:
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        extracted_layout = process_data_with_pdfminer(
            file=fp,
            dpi=dpi,
        )
        return extracted_layout


@requires_dependencies("unstructured_inference")
def process_data_with_pdfminer(
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
) -> List[List["TextRegion"]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    from unstructured_inference.inference.elements import (
        EmbeddedTextRegion,
        ImageTextRegion,
    )

    layouts = []
    # Coefficient to rescale bounding box to be compatible with images
    coef = dpi / 72
    for page, page_layout in open_pdfminer_pages_generator(file):
        height = page_layout.height

        layout: list["TextRegion"] = []
        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)

            if hasattr(obj, "get_text"):
                _text = obj.get_text()
                text_region = _create_text_region(
                    x1, y1, x2, y2, coef, _text, Source.PDFMINER, EmbeddedTextRegion
                )
                if text_region.bbox is not None and text_region.bbox.area > 0:
                    layout.append(text_region)
            else:
                inner_image_objects = extract_image_objects(obj)
                for img_obj in inner_image_objects:
                    new_x1, new_y1, new_x2, new_y2 = rect_to_bbox(img_obj.bbox, height)
                    text_region = _create_text_region(
                        new_x1, new_y1, new_x2, new_y2, coef, None, Source.PDFMINER, ImageTextRegion
                    )
                    if text_region.bbox is not None and text_region.bbox.area > 0:
                        layout.append(text_region)

        # NOTE(christine): always do the basic sort first for deterministic order across
        # python versions.
        layout = sort_text_regions(layout, SORT_MODE_BASIC)

        # apply the current default sorting to the layout elements extracted by pdfminer
        layout = sort_text_regions(layout)

        layouts.append(layout)

    return layouts


def _create_text_region(x1, y1, x2, y2, coef, text, source, region_class):
    """Creates a text region of the specified class with scaled coordinates."""
    return region_class.from_coords(
        x1 * coef,
        y1 * coef,
        x2 * coef,
        y2 * coef,
        text=text,
        source=source,
    )


@requires_dependencies("unstructured_inference")
def merge_inferred_with_extracted_layout(
    inferred_document_layout: "DocumentLayout",
    extracted_layout: List[List["TextRegion"]],
    hi_res_model_name: str,
) -> "DocumentLayout":
    """Merge an inferred layout with an extracted layout"""

    from unstructured_inference.inference.layoutelement import (
        merge_inferred_layout_with_extracted_layout as merge_inferred_with_extracted_page,
    )
    from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel

    # If the model is a chipper model, we don't want to order the
    # elements, as they are already ordered
    order_elements = not hi_res_model_name.startswith("chipper")

    inferred_pages = inferred_document_layout.pages
    for i, (inferred_page, extracted_page_layout) in enumerate(
        zip(inferred_pages, extracted_layout)
    ):
        inferred_layout = inferred_page.elements
        image_metadata = inferred_page.image_metadata
        w = image_metadata.get("width")
        h = image_metadata.get("height")
        image_size = (w, h)

        threshold_kwargs = {}
        # NOTE(Benjamin): With this the thresholds are only changed for detextron2_mask_rcnn
        # In other case the default values for the functions are used
        if (
            isinstance(inferred_page.detection_model, UnstructuredDetectronONNXModel)
            and "R_50" not in inferred_page.detection_model.model_path
        ):
            threshold_kwargs = {"same_region_threshold": 0.5, "subregion_threshold": 0.5}

        merged_layout = merge_inferred_with_extracted_page(
            inferred_layout=inferred_layout,
            extracted_layout=extracted_page_layout,
            page_image_size=image_size,
            **threshold_kwargs,
        )

        if order_elements:
            merged_layout = sort_text_regions(
                cast(List["TextRegion"], merged_layout), SORT_MODE_BASIC
            )

        elements = []
        for layout_el in merged_layout:
            if layout_el.text is None:
                text = aggregate_embedded_text_by_block(
                    text_region=cast("TextRegion", layout_el),
                    pdf_objects=extracted_page_layout,
                )
            else:
                text = layout_el.text
            layout_el.text = remove_control_characters(text)
            elements.append(layout_el)

        inferred_page.elements[:] = elements

    return inferred_document_layout


def clean_pdfminer_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean pdfminer elements from inside tables.

    This function removes elements sourced from PDFMiner that are subregions within table elements.
    """

    for page in document.pages:
        tables = [e for e in page.elements if e.type == ElementType.TABLE]
        for i, element in enumerate(page.elements):
            if element.source != Source.PDFMINER:
                continue
            subregion_threshold = env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD
            element_inside_table = [
                element.bbox.is_almost_subregion_of(t.bbox, subregion_threshold) for t in tables
            ]
            if sum(element_inside_table) == 1:
                page.elements[i] = None
        page.elements = [e for e in page.elements if e]

    return document


def clean_pdfminer_duplicate_image_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Removes duplicate image elements extracted by PDFMiner from a document layout."""

    from unstructured_inference.inference.elements import (
        region_bounding_boxes_are_almost_the_same,
    )

    for page in document.pages:
        image_elements = []
        for i, element in enumerate(page.elements):
            if element.source != Source.PDFMINER or element.type != ElementType.IMAGE:
                continue

            # check if this element is a duplicate
            if any(
                e.text == element.text
                and region_bounding_boxes_are_almost_the_same(
                    e.bbox, element.bbox, env_config.EMBEDDED_IMAGE_SAME_REGION_THRESHOLD
                )
                for e in image_elements
            ):
                page.elements[i] = None
            image_elements.append(element)
        page.elements = [e for e in page.elements if e]

    return document


def aggregate_embedded_text_by_block(
    text_region: "TextRegion",
    pdf_objects: list["TextRegion"],
) -> str:
    """Extracts the text aggregated from the elements of the given layout that lie within the given
    block."""

    subregion_threshold = env_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD
    filtered_blocks = [
        obj
        for obj in pdf_objects
        if obj.bbox.is_almost_subregion_of(text_region.bbox, subregion_threshold)
    ]
    text = " ".join([x.text for x in filtered_blocks if x.text])
    return text
