import tempfile
from typing import Any, BinaryIO, List, Tuple

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTContainer, LTImage
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PSSyntaxError

from unstructured.logger import logger
from unstructured.utils import requires_dependencies


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


def init_pdfminer():
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    return device, interpreter


def process_page(fp: BinaryIO, page, device, interpreter, page_number):
    try:
        interpreter.process_page(page)
        page_layout = device.get_result()
        return page, page_layout
    except PSSyntaxError:
        logger.info("Detected invalid dictionary construct for PDFminer")
        logger.info(f"Repairing the PDF page {page_number + 1} ...")
        # find the error page from binary data fp
        from unstructured.partition.pdf_image.pypdf_utils import get_page_data
        error_page_data = get_page_data(fp, page_number=page_number)
        # repair the error page with pikepdf
        with tempfile.NamedTemporaryFile() as tmp:
            with pikepdf.Pdf.open(error_page_data) as pdf:
                pdf.save(tmp.name)
            page = next(PDFPage.get_pages(open(tmp.name, "rb")))  # noqa: SIM115
            interpreter.process_page(page)
            page_layout = device.get_result()
            return page, page_layout


@requires_dependencies(["pikepdf", "pypdf"])
def open_pdfminer_pages_generator(fp: BinaryIO):
    """Open PDF pages using PDFMiner, handling and repairing invalid dictionary constructs."""

    import pikepdf
    from io import BytesIO

    device, interpreter = init_pdfminer()
    fp = BytesIO(fp.read())
    pages = list(PDFPage.get_pages(fp))

    with ThreadPoolExecutor(max_workers=20) as executor:
        try:
            futures = {executor.submit(process_page, fp, page, device, interpreter, i): i for i, page in enumerate(pages)}

            for future in as_completed(futures):
                page_number = futures[future]
                try:
                    page, page_layout = future.result()
                    yield page, page_layout
                except Exception as e:
                    logger.error(f"Error processing page {page_number + 1}: {e}")
        except Exception as e:
            print(f"페이지 {page_number}에서 오류 발생: {e}")
        finally:
            print('hi shutting down')
            executor.shutdown(wait=True)

    print('toto')