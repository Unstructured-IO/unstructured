from typing import TYPE_CHECKING, BinaryIO, List, Optional, Union, cast

from pdfminer.utils import open_filename

from unstructured.documents.elements import ElementType
from unstructured.partition.pdf_image.pdfminer_utils import (
    get_images_from_pdf_element,
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import Source
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
    from unstructured_inference.inference.ordering import order_layout

    layouts = []
    # Coefficient to rescale bounding box to be compatible with images
    coef = dpi / 72
    for page, page_layout in open_pdfminer_pages_generator(file):
        height = page_layout.height

        layout: List["TextRegion"] = []
        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)

            if hasattr(obj, "get_text"):
                _text = obj.get_text()
                element_class = EmbeddedTextRegion  # type: ignore
            else:
                embedded_images = get_images_from_pdf_element(obj)
                if len(embedded_images) > 0:
                    _text = None
                    element_class = ImageTextRegion  # type: ignore
                else:
                    continue

            text_region = element_class.from_coords(
                x1 * coef,
                y1 * coef,
                x2 * coef,
                y2 * coef,
                text=_text,
                source=Source.PDFMINER,
            )

            if text_region.bbox is not None and text_region.bbox.area > 0:
                layout.append(text_region)

        # NOTE(christine): always do the basic sort first for deterministic order across
        # python versions.
        layout = order_layout(layout)

        # apply the current default sorting to the layout elements extracted by pdfminer
        layout = sort_text_regions(layout)

        layouts.append(layout)

    return layouts


@requires_dependencies("unstructured_inference")
def merge_inferred_with_extracted_layout(
    inferred_document_layout: "DocumentLayout",
    extracted_layout: List[List["TextRegion"]],
) -> "DocumentLayout":
    """Merge an inferred layout with an extracted layout"""

    from unstructured_inference.inference.layoutelement import (
        merge_inferred_layout_with_extracted_layout as merge_inferred_with_extracted_page,
    )
    from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel

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

        elements = inferred_page.get_elements_from_layout(
            layout=cast(List["TextRegion"], merged_layout),
            pdf_objects=extracted_page_layout,
        )

        inferred_page.elements[:] = elements

    return inferred_document_layout


@requires_dependencies("unstructured_inference")
def clean_pdfminer_inner_elements(document: "DocumentLayout") -> "DocumentLayout":
    """Clean pdfminer elements from inside tables.

    This function removes elements sourced from PDFMiner that are subregions within table elements.
    """

    from unstructured_inference.config import inference_config

    for page in document.pages:
        tables = [e for e in page.elements if e.type == ElementType.TABLE]
        for i, element in enumerate(page.elements):
            if element.source != Source.PDFMINER:
                continue
            subregion_threshold = inference_config.EMBEDDED_TEXT_AGGREGATION_SUBREGION_THRESHOLD
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
