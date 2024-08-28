import os
import tempfile
from typing import Any, BinaryIO, List, Tuple

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTContainer, LTImage, LTItem, LTTextLine
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PSSyntaxError

from unstructured.logger import logger
from unstructured.utils import requires_dependencies


def init_pdfminer():
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    return device, interpreter


def extract_image_objects(parent_object: LTItem) -> List[LTImage]:
    """Recursively extracts image objects from a given parent object in a PDF document."""
    objects = []

    if isinstance(parent_object, LTImage):
        objects.append(parent_object)
    elif isinstance(parent_object, LTContainer):
        for child in parent_object:
            objects.extend(extract_image_objects(child))

    return objects


def extract_text_objects(parent_object: LTItem) -> List[LTTextLine]:
    objects = []

    if isinstance(parent_object, LTTextLine):
        objects.append(parent_object)
    elif isinstance(parent_object, LTContainer):
        for child in parent_object:
            objects.extend(extract_text_objects(child))

    return objects


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


@requires_dependencies(["pikepdf", "pypdf"])
def open_pdfminer_pages_generator(
    fp: BinaryIO,
):
    """Open PDF pages using PDFMiner, handling and repairing invalid dictionary constructs."""

    import pikepdf

    from unstructured.partition.pdf_image.pypdf_utils import get_page_data

    device, interpreter = init_pdfminer()
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_file_path = os.path.join(tmp_dir_path, "tmp_file")
        try:
            pages = PDFPage.get_pages(fp)
            # Detect invalid dictionary construct for entire PDF
            for i, page in enumerate(pages):
                try:
                    # Detect invalid dictionary construct for one page
                    interpreter.process_page(page)
                    page_layout = device.get_result()
                except PSSyntaxError:
                    logger.info("Detected invalid dictionary construct for PDFminer")
                    logger.info(f"Repairing the PDF page {i+1} ...")
                    # find the error page from binary data fp
                    error_page_data = get_page_data(fp, page_number=i)
                    # repair the error page with pikepdf
                    with pikepdf.Pdf.open(error_page_data) as pdf:
                        pdf.save(tmp_file_path)
                    page = next(PDFPage.get_pages(open(tmp_file_path, "rb")))  # noqa: SIM115
                    interpreter.process_page(page)
                    page_layout = device.get_result()
                yield page, page_layout
        except PSSyntaxError:
            logger.info("Detected invalid dictionary construct for PDFminer")
            logger.info("Repairing the PDF document ...")
            # repair the entire doc with pikepdf
            with pikepdf.Pdf.open(fp) as pdf:
                pdf.save(tmp_file_path)
            pages = PDFPage.get_pages(open(tmp_file_path, "rb"))  # noqa: SIM115
            for page in pages:
                interpreter.process_page(page)
                page_layout = device.get_result()
                yield page, page_layout


def is_bbox_similar(
    bbox1: tuple[float, float, float, float],
    bbox2: [float, float, float, float],
    threshold: int = 2,
) -> bool:
    """Check if two bounding boxes are similar within a certain threshold."""
    return all(abs(a - b) <= threshold for a, b in zip(bbox1, bbox2))


def is_bbox_subregion(
    bbox1: tuple[float, float, float, float],
    bbox2: [float, float, float, float],
    threshold: int = 2,
) -> bool:
    """Check if bbox1 is a subregion of bbox2."""
    return (
        bbox2[0] - threshold <= bbox1[0] <= bbox2[2] + threshold
        and bbox2[1] - threshold <= bbox1[1] <= bbox2[3] + threshold
        and bbox2[0] - threshold <= bbox1[2] <= bbox2[2] + threshold
        and bbox2[1] - threshold <= bbox1[3] <= bbox2[3] + threshold
    )


def remove_duplicate_objects(objects: list[Any], threshold=2) -> list[Any]:
    """
    Removes duplicate objects based on bounding box similarity.

    This function iterates through a list of objects, each of which is assumed to have a `bbox`
    attribute representing its bounding box as a tuple (x0, y0, x1, y1). It removes objects that
    have bounding boxes similar to others already in the list (based on a specified threshold) or
    are subregions of other objects. The remaining unique objects are returned.
    """
    unique_objects = []

    for obj in objects:
        is_duplicate_or_subregion = False

        for unique_obj in unique_objects:
            if is_bbox_similar(obj.bbox, unique_obj.bbox, threshold) or is_bbox_subregion(
                obj.bbox, unique_obj.bbox, threshold
            ):
                is_duplicate_or_subregion = True
                break

        if not is_duplicate_or_subregion:
            unique_objects.append(obj)

    return unique_objects
