import os
import tempfile
from typing import BinaryIO, List, Optional, Tuple, Union

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTChar, LTContainer, LTImage, LTItem, LTTextLine
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.psexceptions import PSSyntaxError
from pydantic import BaseModel

from unstructured.logger import logger
from unstructured.utils import requires_dependencies


class CustomPDFPageInterpreter(PDFPageInterpreter):
    """a custom pdfminer page interpreter that adds character render mode information to LTChar
    object as `rendermode` attribute. This is intended to be used to detect invisible text."""

    def _patch_current_chars_with_render_mode(self):
        """Add render_mode to recently created LTChar objects"""
        if hasattr(self.device, "cur_item") and self.device.cur_item:
            render_mode = self.textstate.render
            for item in (
                self.device.cur_item._objs if hasattr(self.device.cur_item, "_objs") else []
            ):
                if hasattr(item, "rendermode"):
                    continue  # Already patched
                if isinstance(item, LTChar):
                    item.rendermode = render_mode

    def do_TJ(self, seq):
        super().do_TJ(seq)
        self._patch_current_chars_with_render_mode()

    def do_Tj(self, s):
        super().do_Tj(s)
        self._patch_current_chars_with_render_mode()


class PDFMinerConfig(BaseModel):
    line_overlap: Optional[float] = None
    word_margin: Optional[float] = None
    line_margin: Optional[float] = None
    char_margin: Optional[float] = None


def init_pdfminer(pdfminer_config: Optional[PDFMinerConfig] = None):
    rsrcmgr = PDFResourceManager()

    laparams_kwargs = pdfminer_config.model_dump(exclude_none=True) if pdfminer_config else {}
    laparams = LAParams(**laparams_kwargs)

    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = CustomPDFPageInterpreter(rsrcmgr, device)

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


def _is_duplicate_char(char1: LTChar, char2: LTChar, threshold: float) -> bool:
    """Detect if two characters are duplicates caused by fake bold rendering.

    Some PDF generators create bold text by rendering the same character twice at slightly
    offset positions. This function detects such duplicates by checking if two characters
    have the same text content and nearly identical positions.

    Args:
        char1: First LTChar object.
        char2: Second LTChar object.
        threshold: Maximum pixel distance to consider as duplicate.

    Returns:
        True if char2 appears to be a duplicate of char1.
    """
    # Must be the same character
    if char1.get_text() != char2.get_text():
        return False

    # Check if positions are nearly identical (within threshold)
    x_diff = abs(char1.x0 - char2.x0)
    y_diff = abs(char1.y0 - char2.y0)

    return x_diff < threshold and y_diff < threshold


def deduplicate_chars_in_text_line(text_line: LTTextLine, threshold: float) -> str:
    """Extract text from an LTTextLine with duplicate characters removed.

    Some PDFs create bold text by rendering each character twice at slightly offset
    positions. This function removes such duplicates by keeping only the first instance
    when two identical characters appear at nearly the same position.

    Args:
        text_line: An LTTextLine object containing characters to extract.
        threshold: Maximum pixel distance to consider characters as duplicates.
                   Set to 0 to disable deduplication.

    Returns:
        The extracted text with duplicate characters removed.
    """
    if threshold <= 0:
        return text_line.get_text()

    # Build deduplicated text while preserving non-LTChar items (like LTAnno for spaces)
    result_parts: List[str] = []
    last_ltchar: Optional[LTChar] = None

    for item in text_line:
        if isinstance(item, LTChar):
            # Check if this is a duplicate of the last LTChar
            if last_ltchar is not None and _is_duplicate_char(last_ltchar, item, threshold):
                # Skip this duplicate character
                continue
            last_ltchar = item
            result_parts.append(item.get_text())
        else:
            # Non-LTChar items (e.g., LTAnno for spaces) - keep as-is
            if hasattr(item, "get_text"):
                result_parts.append(item.get_text())

    return "".join(result_parts)


def get_text_with_deduplication(
    text_obj: Union[LTTextLine, LTContainer, LTItem],
    threshold: float,
) -> str:
    """Get text from a text object with optional character deduplication.

    This is the main entry point for extracting text with fake-bold deduplication.
    It handles LTTextLine objects and recursively processes containers.

    Args:
        text_obj: An LTTextLine, LTContainer, or other LTItem object.
        threshold: Maximum pixel distance to consider characters as duplicates.
                   Set to 0 to disable deduplication.

    Returns:
        The extracted text with duplicate characters removed.
    """
    if isinstance(text_obj, LTTextLine):
        return deduplicate_chars_in_text_line(text_obj, threshold)
    elif isinstance(text_obj, LTContainer):
        parts: List[str] = []
        for child in text_obj:
            if isinstance(child, LTTextLine):
                parts.append(deduplicate_chars_in_text_line(child, threshold))
            elif hasattr(child, "get_text"):
                parts.append(child.get_text())
        return "".join(parts)
    elif hasattr(text_obj, "get_text"):
        return text_obj.get_text()
    return ""


@requires_dependencies(["pikepdf", "pypdf"])
def open_pdfminer_pages_generator(
    fp: BinaryIO, password: Optional[str] = None, pdfminer_config: Optional[PDFMinerConfig] = None
):
    """Open PDF pages using PDFMiner, handling and repairing invalid dictionary constructs."""

    import pikepdf

    from unstructured.partition.pdf_image.pypdf_utils import get_page_data

    device, interpreter = init_pdfminer(pdfminer_config=pdfminer_config)
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_file_path = os.path.join(tmp_dir_path, "tmp_file")
        try:
            pages = PDFPage.get_pages(fp, password=password or "")
            # Detect invalid dictionary construct for entire PDF
            for i, page in enumerate(pages):
                try:
                    # Detect invalid dictionary construct for one page
                    interpreter.process_page(page)
                    page_layout = device.get_result()
                except PSSyntaxError:
                    logger.info("Detected invalid dictionary construct for PDFminer")
                    logger.info(f"Repairing the PDF page {i + 1} ...")
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
