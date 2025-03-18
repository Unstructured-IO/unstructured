from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pandas as pd
import unstructured_pytesseract
from lxml import etree
from PIL import Image as PILImage

from unstructured.logger import trace_logger
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import (
    IMAGE_COLOR_DEPTH,
    TESSERACT_MAX_SIZE,
    TESSERACT_TEXT_HEIGHT,
    Source,
)
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegions
    from unstructured_inference.inference.layoutelement import LayoutElements

# -- force tesseract to be single threaded, otherwise we see major performance problems --
if "OMP_THREAD_LIMIT" not in os.environ:
    os.environ["OMP_THREAD_LIMIT"] = "1"


class OCRAgentTesseract(OCRAgent):
    """OCR service implementation for Tesseract."""

    hocr_namespace = {"h": "http://www.w3.org/1999/xhtml"}

    def __init__(self, language: str = "eng"):
        self.language = language

    def is_text_sorted(self):
        return True

    def get_text_from_image(self, image: PILImage.Image) -> str:
        return unstructured_pytesseract.image_to_string(np.array(image), lang=self.language)

    def get_layout_from_image(self, image: PILImage.Image) -> TextRegions:
        """Get the OCR regions from image as a list of text regions with tesseract."""

        trace_logger.detail("Processing entire page OCR with tesseract...")
        zoom = 1
        ocr_df: pd.DataFrame = self.image_to_data_with_character_confidence_filter(
            np.array(image),
            lang=self.language,
            character_confidence_threshold=env_config.TESSERACT_CHARACTER_CONFIDENCE_THRESHOLD,
        )
        ocr_df = ocr_df.dropna()

        # tesseract performance degrades when the text height is out of the preferred zone so we
        # zoom the image (in or out depending on estimated text height) for optimum OCR results
        # but this needs to be evaluated based on actual use case as the optimum scaling also
        # depend on type of characters (font, language, etc); be careful about this
        # functionality
        text_height = ocr_df[TESSERACT_TEXT_HEIGHT].quantile(
            env_config.TESSERACT_TEXT_HEIGHT_QUANTILE
        )
        if (
            text_height < env_config.TESSERACT_MIN_TEXT_HEIGHT
            or text_height > env_config.TESSERACT_MAX_TEXT_HEIGHT
        ):
            max_zoom = max(
                0,
                np.round(np.sqrt(TESSERACT_MAX_SIZE / np.prod(image.size) / IMAGE_COLOR_DEPTH), 1),
            )
            # rounding avoids unnecessary precision and potential numerical issues associated
            # with numbers very close to 1 inside cv2 image processing
            zoom = min(
                np.round(env_config.TESSERACT_OPTIMUM_TEXT_HEIGHT / text_height, 1),
                max_zoom,
            )
            ocr_df = self.image_to_data_with_character_confidence_filter(
                np.array(zoom_image(image, zoom)),
                lang=self.language,
                character_confidence_threshold=env_config.TESSERACT_CHARACTER_CONFIDENCE_THRESHOLD,
            )
            ocr_df = ocr_df.dropna()
        ocr_regions = self.parse_data(ocr_df, zoom=zoom)

        return ocr_regions

    def image_to_data_with_character_confidence_filter(
        self,
        image: np.ndarray,
        lang: str = "eng",
        config: str = "",
        character_confidence_threshold: float = 0.0,
    ) -> pd.DataFrame:
        hocr: str = unstructured_pytesseract.image_to_pdf_or_hocr(
            image,
            lang=lang,
            config="-c hocr_char_boxes=1 " + config,
            extension="hocr",
        )
        ocr_df = self.hocr_to_dataframe(hocr, character_confidence_threshold)
        return ocr_df

    def hocr_to_dataframe(
        self, hocr: str, character_confidence_threshold: float = 0.0
    ) -> pd.DataFrame:

        df_entries = []

        if not hocr:
            return pd.DataFrame(df_entries, columns=["left", "top", "width", "height", "text"])

        root = etree.fromstring(hocr)
        word_spans = root.findall('.//h:span[@class="ocrx_word"]', self.hocr_namespace)

        for word_span in word_spans:
            word_title = word_span.get("title", "")
            bbox_match = re.search(r"bbox (\d+) (\d+) (\d+) (\d+)", word_title)

            text = self.extract_word_from_hocr(
                word=word_span, character_confidence_threshold=character_confidence_threshold
            )
            if text and bbox_match:
                word_bbox = list(map(int, bbox_match.groups()))
                left, top, right, bottom = word_bbox
                df_entries.append(
                    {
                        "left": left,
                        "top": top,
                        "right": right,
                        "bottom": bottom,
                        "text": text,
                    }
                )
        ocr_df = pd.DataFrame(df_entries, columns=["left", "top", "right", "bottom", "text"])

        ocr_df["width"] = ocr_df["right"] - ocr_df["left"]
        ocr_df["height"] = ocr_df["bottom"] - ocr_df["top"]

        ocr_df = ocr_df.drop(columns=["right", "bottom"])
        return ocr_df

    def extract_word_from_hocr(
        self, word: etree.Element, character_confidence_threshold: float = 0.0
    ) -> str:
        """Extracts a word from an hOCR word tag, filtering out characters with low confidence."""

        character_spans = word.findall('.//h:span[@class="ocrx_cinfo"]', self.hocr_namespace)
        if len(character_spans) == 0:
            return ""

        word_text = ""
        for character_span in character_spans:
            char = character_span.text

            char_title = character_span.get("title", "")
            conf_match = re.search(r"x_conf (\d+\.\d+)", char_title)

            if not (char and conf_match):
                continue

            character_probability = float(conf_match.group(1)) / 100

            if character_probability >= character_confidence_threshold:
                word_text += char

        return word_text

    @requires_dependencies("unstructured_inference")
    def get_layout_elements_from_image(self, image: PILImage.Image) -> LayoutElements:
        from unstructured.partition.pdf_image.inference_utils import (
            build_layout_elements_from_ocr_regions,
        )

        ocr_regions = self.get_layout_from_image(image)

        # NOTE(christine): For tesseract, the ocr_text returned by
        # `unstructured_pytesseract.image_to_string()` doesn't contain bounding box data but is
        # well grouped. Conversely, the ocr_layout returned by parsing
        # `unstructured_pytesseract.image_to_data()` contains bounding box data but is not well
        # grouped. Therefore, we need to first group the `ocr_layout` by `ocr_text` and then merge
        # the text regions in each group to create a list of layout elements.

        ocr_text = self.get_text_from_image(image)

        return build_layout_elements_from_ocr_regions(
            ocr_regions=ocr_regions,
            ocr_text=ocr_text,
            group_by_ocr_text=True,
        )

    @requires_dependencies("unstructured_inference")
    def parse_data(self, ocr_data: pd.DataFrame, zoom: float = 1) -> TextRegions:
        """Parse the OCR result data to extract a list of TextRegion objects from tesseract.

        The function processes the OCR result data frame, looking for bounding
        box information and associated text to create instances of the TextRegion
        class, which are then appended to a list.

        Parameters:
        - ocr_data (pd.DataFrame):
            A Pandas DataFrame containing the OCR result data.
            It should have columns like 'text', 'left', 'top', 'width', and 'height'.

        - zoom (float, optional):
            A zoom factor to scale the coordinates of the bounding boxes from image scaling.
            Default is 1.

        Returns:
        - TextRegions:
            TextRegions object, containing data from all text regions in numpy arrays; each row
            represents a detected text region within the OCR-ed image.

        Note:
        - An empty string or a None value for the 'text' key in the input
          data frame will result in its associated bounding box being ignored.
        """

        from unstructured_inference.inference.elements import TextRegions

        if zoom <= 0:
            zoom = 1

        texts = ocr_data.text.apply(
            lambda text: str(text) if not isinstance(text, str) else text.strip()
        ).values
        mask = texts != ""
        element_coords = ocr_data[["left", "top", "width", "height"]].values
        element_coords[:, 2] += element_coords[:, 0]
        element_coords[:, 3] += element_coords[:, 1]
        element_coords = element_coords.astype(float) / zoom
        return TextRegions(
            element_coords=element_coords[mask],
            texts=texts[mask],
            sources=np.array([Source.OCR_TESSERACT] * mask.sum()),
        )


def zoom_image(image: PILImage.Image, zoom: float = 1) -> PILImage.Image:
    """scale an image based on the zoom factor using cv2; the scaled image is post processed by
    dilation then erosion to improve edge sharpness for OCR tasks"""
    if zoom <= 0:
        # no zoom but still does dilation and erosion
        zoom = 1
    new_image = cv2.resize(
        cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR),
        None,
        fx=zoom,
        fy=zoom,
        interpolation=cv2.INTER_CUBIC,
    )

    kernel = np.ones((1, 1), np.uint8)
    new_image = cv2.dilate(new_image, kernel, iterations=1)
    new_image = cv2.erode(new_image, kernel, iterations=1)

    return PILImage.fromarray(new_image)
