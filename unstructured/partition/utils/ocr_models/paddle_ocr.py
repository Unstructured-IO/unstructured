from typing import TYPE_CHECKING, List

import numpy as np
from PIL import Image as PILImage

from unstructured.documents.elements import ElementType
from unstructured.logger import logger
from unstructured.partition.utils.constants import (
    DEFAULT_PADDLE_LANG,
    Source,
)
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layoutelement import LayoutElement


class OCRAgentPaddle(OCRAgent):
    def load_agent(self, language: str = DEFAULT_PADDLE_LANG):
        import paddle
        from unstructured_paddleocr import PaddleOCR

        """Loads the PaddleOCR agent as a global variable to ensure that we only load it once."""

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

    def get_text_from_image(self, image: PILImage, ocr_languages: str = "eng") -> str:
        ocr_regions = self.get_layout_from_image(image)
        return "\n\n".join([r.text for r in ocr_regions])

    def is_text_sorted(self):
        return False

    def get_layout_from_image(
        self, image: PILImage, ocr_languages: str = "eng"
    ) -> List["TextRegion"]:
        """Get the OCR regions from image as a list of text regions with paddle."""

        logger.info("Processing entire page OCR with paddle...")

        # TODO(yuming): pass in language parameter once we
        # have the mapping for paddle lang code
        # see CORE-2034
        ocr_data = self.agent.ocr(np.array(image), cls=True)
        ocr_regions = self.parse_data(ocr_data)

        return ocr_regions

    @requires_dependencies("unstructured_inference")
    def get_layout_elements_from_image(
        self, image: PILImage, ocr_languages: str = "eng"
    ) -> List["LayoutElement"]:
        from unstructured.partition.pdf_image.inference_utils import build_layout_element

        ocr_regions = self.get_layout_from_image(
            image,
            ocr_languages=ocr_languages,
        )

        # NOTE(christine): For paddle, there is no difference in `ocr_layout` and `ocr_text` in
        # terms of grouping because we get ocr_text from `ocr_layout, so the first two grouping
        # and merging steps are not necessary.
        return [
            build_layout_element(
                bbox=r.bbox,
                text=r.text,
                source=r.source,
                element_type=ElementType.UNCATEGORIZED_TEXT,
            )
            for r in ocr_regions
        ]

    @requires_dependencies("unstructured_inference")
    def parse_data(self, ocr_data: list) -> List["TextRegion"]:
        """
        Parse the OCR result data to extract a list of TextRegion objects from
        paddle.

        The function processes the OCR result dictionary, looking for bounding
        box information and associated text to create instances of the TextRegion
        class, which are then appended to a list.

        Parameters:
        - ocr_data (list): A list containing the OCR result data

        Returns:
        - List[TextRegion]: A list of TextRegion objects, each representing a
                            detected text region within the OCR-ed image.

        Note:
        - An empty string or a None value for the 'text' key in the input
          dictionary will result in its associated bounding box being ignored.
        """

        from unstructured.partition.pdf_image.inference_utils import build_text_region_from_coords

        text_regions = []
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
                        x1,
                        y1,
                        x2,
                        y2,
                        text=cleaned_text,
                        source=Source.OCR_PADDLE,
                    )
                    text_regions.append(text_region)

        return text_regions
