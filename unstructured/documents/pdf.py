from __future__ import annotations
from typing import List, Optional, Union

import layoutparser as lp
import numpy as np
from PIL import Image

from unstructured.logger import get_logger
from unstructured.documents.base import Document, Page
from unstructured.documents.elements import Element, NarrativeText, Title
import unstructured.models.ocr.tesseract as tesseract
import unstructured.models.layout.detectron2 as detectron2

logger = get_logger()


class PDFDocument(Document):
    """Class for handling documents that are saved as .pdf files. For .pdf files, a
    document image analysis (DIA) model detects the layout of the page prior to extracting
    element."""

    def __init__(self):
        print(
            """

======================================================================
WARNING: PDF parsing capabilities in unstructured is still experimental
======================================================================

"""
        )
        super().__init__()

    @classmethod
    def from_file(cls, filename: str):
        logger.info(f"Reading PDF for file: {filename} ...")
        layouts, images = lp.load_pdf(filename, load_images=True)
        pages: List[Page] = list()
        for i, layout in enumerate(layouts):
            image = images[i]
            # NOTE(robinson) - In the future, maybe we detect the page number and default
            # to the index if it is not detected
            page = PDFPage(number=i, image=image, layout=layout)
            page.get_elements()
            pages.append(page)
        return cls.from_pages(pages)


class PDFPage(Page):
    """Class for an individual PDF page."""

    def __init__(self, number: int, image: Image, layout: lp.Layout):
        self.image = image
        self.image_array: Union[np.ndarray, None] = None
        self.layout = layout
        super().__init__(number=number)

    def get_elements(self, inplace=True) -> Optional[List[Element]]:
        """Uses a layoutparser model to detect the elements on the page."""
        logger.info("Detecting page elements ...")
        detectron2.load_model()

        elements: List[Element] = list()
        # NOTE(mrobinson) - We'll want make this model inference step some kind of
        # remote call in the future.
        image_layout = detectron2.model.detect(self.image)
        # NOTE(robinson) - This orders the page from top to bottom. We'll need more
        # sophisticated ordering logic for more complicated layouts.
        image_layout.sort(key=lambda element: element.coordinates[1], inplace=True)
        for item in image_layout:
            if item.type in ["Text", "Title"]:
                text_blocks = self.layout.filter_by(item, center=True)
                text = str()
                for text_block in text_blocks:
                    # NOTE(robinson) - If the text attribute is None, that means the PDF isn't
                    # already OCR'd and we have to send the snippet out for OCRing.
                    if text_block.text is None:
                        text_block.text = self.ocr(text_block)
                text = " ".join([x for x in text_blocks.get_texts() if x])

                if item.type == "Text":
                    elements.append(NarrativeText(text=text))
                elif item.type == "Title":
                    elements.append(Title(text=text))

        if inplace:
            self.elements = elements
            return None
        return elements

    def ocr(self, text_block: lp.TextBlock) -> str:
        """Runs a cropped text block image through and OCR agent."""
        logger.debug("Running OCR on text block ...")
        tesseract.load_agent()
        image_array = self._get_image_array()
        padded_block = text_block.pad(left=5, right=5, top=5, bottom=5)
        cropped_image = padded_block.crop_image(image_array)
        return tesseract.ocr_agent.detect(cropped_image)

    def _get_image_array(self) -> Union[np.ndarray, None]:
        """Converts the raw image into a numpy array."""
        if self.image_array is None:
            self.image_array = np.array(self.image)
        return self.image_array
