from typing import TYPE_CHECKING, BinaryIO, List, Optional, Union, cast

from pdfminer.utils import open_filename
from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    ImageTextRegion,
    TextRegion,
)
from unstructured_inference.inference.layoutelement import (
    merge_inferred_layout_with_extracted_layout as merge_inferred_with_extracted_page,
)
from unstructured_inference.inference.ordering import order_layout
from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel

from unstructured.partition.pdf_image.pdfminer_utils import (
    get_images_from_pdf_element,
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.utils.constants import Source
from unstructured.partition.utils.sorting import sort_text_regions

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout


def process_file_with_pdfminer(
    filename: str = "",
    dpi: int = 200,
) -> List[List[TextRegion]]:
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        extracted_layout = process_data_with_pdfminer(
            file=fp,
            dpi=dpi,
        )
        return extracted_layout


def process_data_with_pdfminer(
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
) -> List[List[TextRegion]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

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


def merge_inferred_with_extracted_layout(
    inferred_document_layout: "DocumentLayout",
    extracted_layout: List[List[TextRegion]],
) -> "DocumentLayout":
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
            layout=cast(List[TextRegion], merged_layout),
            pdf_objects=extracted_page_layout,
        )

        inferred_page.elements[:] = elements

    return inferred_document_layout
