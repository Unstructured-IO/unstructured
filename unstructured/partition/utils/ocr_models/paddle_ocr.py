from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from PIL import Image as PILImage

from unstructured.documents.elements import ElementType
from unstructured.logger import logger, trace_logger
from unstructured.partition.utils.constants import Source
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion, TextRegions
    from unstructured_inference.inference.layoutelement import LayoutElements


class OCRAgentPaddle(OCRAgent):
    """OCR service implementation for PaddleOCR."""

    def __init__(self, language: str = "en"):
        self.agent = self.load_agent(language)

    def load_agent(self, language: str):
        """Loads the PaddleOCR agent as a global variable to ensure that we only load it once."""

        import paddle
        from unstructured_paddleocr import PaddleOCR

        # Disable signal handlers at C++ level upon failing
        # ref: https://www.paddlepaddle.org.cn/documentation/docs/en/api/paddle/
        #      disable_signal_handler_en.html#disable-signal-handler
        paddle.disable_signal_handler()
        # Use paddlepaddle-gpu if there is gpu device available
        gpu_available = paddle.device.cuda.device_count() > 0
        if gpu_available:
            logger.info(f"Loading paddle with GPU on language={language}...")
        else:
            logger.info(f"Loading paddle with CPU on language={language}...")
        try:
            # Enable MKL-DNN for paddle to speed up OCR if OS supports it
            # ref: https://paddle-inference.readthedocs.io/en/master/
            #      api_reference/cxx_api_doc/Config/CPUConfig.html
            paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                use_gpu=gpu_available,
                lang=language,
                enable_mkldnn=True,
                show_log=False,
            )
        except AttributeError:
            paddle_ocr = PaddleOCR(
                use_angle_cls=True,
                use_gpu=gpu_available,
                lang=language,
                enable_mkldnn=False,
                show_log=False,
            )
        return paddle_ocr

    def get_text_from_image(self, image: PILImage.Image) -> str:
        ocr_regions = self.get_layout_from_image(image)
        return "\n\n".join(ocr_regions.texts)

    def is_text_sorted(self):
        return False

    def get_layout_from_image(self, image: PILImage.Image) -> TextRegions:
        """Get the OCR regions from image as a list of text regions with paddle."""

        trace_logger.detail("Processing entire page OCR with paddle...")

        # TODO(yuming): pass in language parameter once we
        # have the mapping for paddle lang code
        # see CORE-2034
        ocr_data = self.agent.ocr(np.array(image), cls=True)
        ocr_regions = self.parse_data(ocr_data)

        return ocr_regions

    @requires_dependencies("unstructured_inference")
    def get_layout_elements_from_image(self, image: PILImage.Image) -> LayoutElements:

        ocr_regions = self.get_layout_from_image(image)

        # NOTE(christine): For paddle, there is no difference in `ocr_layout` and `ocr_text` in
        # terms of grouping because we get ocr_text from `ocr_layout, so the first two grouping
        # and merging steps are not necessary.
        return LayoutElements(
            element_coords=ocr_regions.element_coords,
            texts=ocr_regions.texts,
            element_class_ids=np.zeros(ocr_regions.texts.shape),
            element_class_id_map={0: ElementType.UNCATEGORIZED_TEXT},
        )

    @requires_dependencies("unstructured_inference")
    def parse_data(self, ocr_data: list[Any]) -> TextRegions:
        """Parse the OCR result data to extract a list of TextRegion objects from paddle.

        The function processes the OCR result dictionary, looking for bounding
        box information and associated text to create instances of the TextRegion
        class, which are then appended to a list.

        Parameters:
        - ocr_data (list): A list containing the OCR result data

        Returns:
        - TextRegions:
            TextRegions object, containing data from all text regions in numpy arrays; each row
            represents a detected text region within the OCR-ed image.

        Note:
        - An empty string or a None value for the 'text' key in the input
          dictionary will result in its associated bounding box being ignored.
        """

        from unstructured_inference.inference.elements import TextRegions

        from unstructured.partition.pdf_image.inference_utils import build_text_region_from_coords

        text_regions: list[TextRegion] = []
        for idx in range(len(ocr_data)):
            res = ocr_data[idx]
            if not res:
                continue

            for line in res:
                x1 = min([i[0] for i in line[0]])
                y1 = min([i[1] for i in line[0]])
                x2 = max([i[0] for i in line[0]])
                y2 = max([i[1] for i in line[0]])
                text = line[1][0]
                if not text:
                    continue
                cleaned_text = text.strip()
                if cleaned_text:
                    text_region = build_text_region_from_coords(
                        x1, y1, x2, y2, text=cleaned_text, source=Source.OCR_PADDLE
                    )
                    text_regions.append(text_region)

        # FIXME (yao): find out if paddle supports a vectorized output format so we can skip the
        # step of parsing a list
        return TextRegions.from_list(text_regions)
