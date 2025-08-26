from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Optional

from google.cloud.vision import Image, ImageAnnotatorClient, ImageContext, Paragraph, TextAnnotation

from unstructured.logger import logger, trace_logger
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import Source
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from unstructured_inference.inference.elements import TextRegion, TextRegions
    from unstructured_inference.inference.layoutelement import LayoutElements


class OCRAgentGoogleVision(OCRAgent):
    """OCR service implementation for Google Vision API."""

    def __init__(self, language: Optional[str] = None) -> None:
        self.language = language
        client_options = {}
        api_endpoint = env_config.GOOGLEVISION_API_ENDPOINT
        if api_endpoint:
            logger.info(f"Using Google Vision OCR with endpoint {api_endpoint}")
            client_options["api_endpoint"] = api_endpoint
        else:
            logger.info("Using Google Vision OCR with default endpoint")
        self.client = ImageAnnotatorClient(client_options=client_options)

    def is_text_sorted(self) -> bool:
        return True

    def get_text_from_image(self, image: PILImage.Image) -> str:
        image_context = ImageContext(language_hints=[self.language]) if self.language else None
        with BytesIO() as buffer:
            image.save(buffer, format="PNG")
            response = self.client.document_text_detection(
                image=Image(content=buffer.getvalue()), image_context=image_context
            )
        document = response.full_text_annotation
        assert isinstance(document, TextAnnotation)
        return document.text

    def get_layout_from_image(self, image: PILImage.Image) -> TextRegions:
        trace_logger.detail("Processing entire page OCR with Google Vision API...")
        image_context = ImageContext(language_hints=[self.language]) if self.language else None
        with BytesIO() as buffer:
            image.save(buffer, format="PNG")
            response = self.client.document_text_detection(
                image=Image(content=buffer.getvalue()), image_context=image_context
            )
        document = response.full_text_annotation
        assert isinstance(document, TextAnnotation)
        regions = self._parse_regions(document)
        return regions

    def get_layout_elements_from_image(self, image: PILImage.Image) -> LayoutElements:
        from unstructured.partition.pdf_image.inference_utils import (
            build_layout_elements_from_ocr_regions,
        )

        ocr_regions = self.get_layout_from_image(
            image,
        )
        ocr_text = self.get_text_from_image(
            image,
        )
        return build_layout_elements_from_ocr_regions(
            ocr_regions=ocr_regions,
            ocr_text=ocr_text,
            group_by_ocr_text=False,
        )

    def _parse_regions(self, ocr_data: TextAnnotation) -> TextRegions:
        from unstructured_inference.inference.elements import TextRegions

        from unstructured.partition.pdf_image.inference_utils import build_text_region_from_coords

        text_regions: list[TextRegion] = []
        for page_idx, page in enumerate(ocr_data.pages):
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    vertices = paragraph.bounding_box.vertices
                    x1, y1 = vertices[0].x, vertices[0].y
                    x2, y2 = vertices[2].x, vertices[2].y
                    text_region = build_text_region_from_coords(
                        x1,
                        y1,
                        x2,
                        y2,
                        text=self._get_text_from_paragraph(paragraph),
                        source=Source.OCR_GOOGLEVISION,
                    )
                    text_regions.append(text_region)
        return TextRegions.from_list(text_regions)

    def _get_text_from_paragraph(self, paragraph: Paragraph) -> str:
        breaks = TextAnnotation.DetectedBreak.BreakType
        para = ""
        line = ""
        for word in paragraph.words:
            for symbol in word.symbols:
                line += symbol.text
                if symbol.property.detected_break.type_ == breaks.SPACE:
                    line += " "
                if symbol.property.detected_break.type_ == breaks.EOL_SURE_SPACE:
                    line += " "
                    para += line
                    line = ""
                if symbol.property.detected_break.type_ == breaks.LINE_BREAK:
                    para += line
                    line = ""
        return para
