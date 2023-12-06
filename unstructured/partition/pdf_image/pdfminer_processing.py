from typing import TYPE_CHECKING, BinaryIO, List, Optional, Union, cast

from pdfminer.utils import open_filename
from unstructured_inference.inference.elements import (
    EmbeddedTextRegion,
    ImageTextRegion,
    TextRegion,
)
from unstructured_inference.inference.layoutelement import (
    merge_inferred_layout_with_extracted_layout,
)
from unstructured_inference.inference.ordering import order_layout
from unstructured_inference.models.detectron2onnx import UnstructuredDetectronONNXModel

from unstructured.partition.pdf_image.pdfminer_utils import (
    get_images_from_pdf_element,
    open_pdfminer_pages_generator,
    rect_to_bbox,
)
from unstructured.partition.utils.constants import Source
from unstructured.partition.utils.sorting import shrink_bbox
from unstructured.partition.utils.xycut import recursive_xy_cut, recursive_xy_cut_swapped

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout


def process_file_with_pdfminer(
    inferred_document_layout: "DocumentLayout",
    filename: str = "",
    is_image: bool = False,
) -> "DocumentLayout":
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        inferred_document_layout = process_data_with_pdfminer(
            inferred_document_layout=inferred_document_layout,
            file=fp,
            is_image=is_image,
        )
        return inferred_document_layout


def process_data_with_pdfminer(
    inferred_document_layout: "DocumentLayout",
    file: Optional[Union[bytes, BinaryIO]] = None,
    is_image: bool = False,
) -> "DocumentLayout":
    if is_image:
        for page in inferred_document_layout.pages:
            for el in page.elements:
                el.text = el.text or ""
        return inferred_document_layout

    extracted_layouts = get_regions_by_pdfminer(file)

    inferred_pages = inferred_document_layout.pages
    for i, (inferred_page, extracted_layout) in enumerate(zip(inferred_pages, extracted_layouts)):
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

        merged_layout = merge_inferred_layout_with_extracted_layout(
            inferred_layout=inferred_layout,
            extracted_layout=extracted_layout,
            page_image_size=image_size,
            **threshold_kwargs,
        )

        elements = inferred_page.get_elements_from_layout(
            layout=cast(List[TextRegion], merged_layout),
            pdf_objects=extracted_layout,
        )

        inferred_page.elements[:] = elements

    return inferred_document_layout


def get_regions_by_pdfminer(
    fp: Optional[Union[bytes, BinaryIO]],
    dpi: int = 200,
) -> List[List[TextRegion]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    import numpy as np

    layouts = []
    # Coefficient to rescale bounding box to be compatible with images
    coef = dpi / 72
    for page, page_layout in open_pdfminer_pages_generator(fp):
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

        layout = order_layout(layout)

        shrink_factor = 0.9
        xy_cut_primary_direction = "x"

        bboxes = [
            (text_region.bbox.x1, text_region.bbox.y1, text_region.bbox.x2, text_region.bbox.y2)
            for text_region in layout
        ]

        shrunken_bboxes = []
        for bbox in bboxes:
            shrunken_bbox = shrink_bbox(bbox, shrink_factor)
            shrunken_bboxes.append(shrunken_bbox)

        res: List[int] = []
        xy_cut_sorting_func = (
            recursive_xy_cut_swapped if xy_cut_primary_direction == "x" else recursive_xy_cut
        )
        xy_cut_sorting_func(
            np.asarray(shrunken_bboxes).astype(int),
            np.arange(len(shrunken_bboxes)),
            res,
        )
        layout = [layout[i] for i in res]
        layouts.append(layout)

    return layouts
