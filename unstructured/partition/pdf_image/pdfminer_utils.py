import os
import tempfile
from typing import BinaryIO, List, Tuple

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
    """Recursively extracts text objects from a given parent object in a PDF document."""
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
