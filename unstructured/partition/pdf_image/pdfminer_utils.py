import os
from typing import BinaryIO, List, Optional, Tuple

import playa
from paves.miner import LAParams, LTContainer, LTImage, LTItem, LTTextLine, extract_page
from pydantic import BaseModel

from unstructured.utils import requires_dependencies


class PDFMinerConfig(BaseModel):
    line_overlap: Optional[float] = None
    word_margin: Optional[float] = None
    line_margin: Optional[float] = None
    char_margin: Optional[float] = None


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


@requires_dependencies("paves")
def open_pdfminer_pages_generator(
    fp: Optional[BinaryIO] = None,
    filename: Optional[str] = None,
    password: Optional[str] = None,
    pdfminer_config: Optional[PDFMinerConfig] = None,
):
    """Open PDF pages using PDFMiner, handling and repairing invalid dictionary constructs."""
    laparams_kwargs = pdfminer_config.model_dump(exclude_none=True) if pdfminer_config else {}
    laparams = LAParams(**laparams_kwargs)
    if password is None:
        password = ""  # playa's default

    if fp is None:
        from functools import partial

        assert filename
        with playa.open(
            filename, space="page", password=password, max_workers=min(1, os.cpu_count() // 2)
        ) as doc:
            yield from zip(doc.pages, doc.pages.map(partial(extract_page, laparams=laparams)))
    else:
        doc = playa.Document(fp, space="page", password=password)
        for page in doc.pages:
            page_layout = extract_page(page, laparams)
            yield page, page_layout
