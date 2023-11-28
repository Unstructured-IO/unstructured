from typing import Any, List, Optional, Union, Tuple, cast, BinaryIO, TYPE_CHECKING

from pdfminer.layout import LTImage, LTContainer, LAParams
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.converter import PDFPageAggregator
from pdfminer.utils import open_filename

from unstructured.partition.utils.constants import Source

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion


def init_pdfminer():
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    return device, interpreter


def get_images_from_pdf_element(layout_object: Any) -> List[LTImage]:
    """
    Recursively extracts LTImage objects from a PDF layout element.

    This function takes a PDF layout element (could be LTImage or LTContainer) and recursively
    extracts all LTImage objects contained within it.

    Parameters:
    - layout_object (Any): The PDF layout element to extract images from.

    Returns:
    - List[LTImage]: A list of LTImage objects extracted from the layout object.

    Note:
    - This function recursively traverses through the layout_object to find and accumulate all
     LTImage objects.
    - If the input layout_object is an LTImage, it will be included in the returned list.
    - If the input layout_object is an LTContainer, the function will recursively search its
     children for LTImage objects.
    - If the input layout_object is neither LTImage nor LTContainer, an empty list will be
     returned.
    """

    # recursively locate Image objects in layout_object
    if isinstance(layout_object, LTImage):
        return [layout_object]
    if isinstance(layout_object, LTContainer):
        img_list: List[LTImage] = []
        for child in layout_object:
            img_list = img_list + get_images_from_pdf_element(child)
        return img_list
    else:
        return []


def process_file_with_pdfminer(
    filename,
) -> Tuple[List[List["TextRegion"]], List[Tuple]]:
    with open_filename(filename, "rb") as fp:
        fp = cast(BinaryIO, fp)
        extracted_regions, image_sizes = process_data_with_pdfminer(fp)

    return extracted_regions, image_sizes


def process_data_with_pdfminer(
    fp: Optional[Union[bytes, BinaryIO]],
    dpi: int = 200,
) -> Tuple[List[List["TextRegion"]], List[Tuple]]:
    """Loads the image and word objects from a pdf using pdfplumber and the image renderings of the
    pdf pages using pdf2image"""

    from unstructured_inference.inference.elements import EmbeddedTextRegion, ImageTextRegion
    from unstructured_inference.inference.ordering import order_layout

    device, interpreter = init_pdfminer()
    layouts = []
    image_sizes = []
    for i, page in enumerate(PDFPage.get_pages(fp)):  # type: ignore
        interpreter.process_page(page)
        page_layout = device.get_result()

        width, height = page_layout.width, page_layout.height

        layout: List["TextRegion"] = []
        page_image_size = (width, height)
        for obj in page_layout:
            x1, y1, x2, y2 = rect_to_bbox(obj.bbox, height)
            # Coefficient to rescale bounding box to be compatible with images
            coef = dpi / 72

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
        layouts.append(layout)
        image_sizes.append(page_image_size)

    return layouts, image_sizes


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
