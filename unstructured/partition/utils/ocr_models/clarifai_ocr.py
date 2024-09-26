from typing import TYPE_CHECKING, List, Optional

import numpy as np
from PIL import Image as PILImage
from clarifai.client.model import Model
from unstructured.documents.elements import ElementType
from unstructured.logger import logger
from unstructured.partition.utils.constants import (
    DEFAULT_PADDLE_LANG,
    Source,
    OCR_DEFAULT_CLARIFAI_MODEL_URL
)
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.utils import requires_dependencies

if TYPE_CHECKING:
    from unstructured_inference.inference.elements import TextRegion
    from unstructured_inference.inference.layoutelement import LayoutElemen



class OCRAgentClarifai(OCRAgent):
    def load_agent(self):
        pass

    def is_text_sorted(self):
        return False

    def get_text_from_image(self, image: PILImage, ocr_languages: str = "eng") -> str:
        ocr_regions = self.get_layout_from_image(image)
        return "\n\n".join([r.text for r in ocr_regions])

    def get_layout_from_image(
        self, image: PILImage, clarifai_model_url: Optional[str] =None, ocr_languages: str = "eng",
    ) -> List["TextRegion"]:
        """Get the OCR regions from image as a list of text regions with paddle."""
        import base64
        logger.info("Processing entire page OCR with paddle...")

        image_bytes = self.pil_image_to_bytes(image)
        ocr_data = Model(clarifai_model_url).predict_by_bytes(image_bytes , input_type="image")
        ocr_regions = self.parse_data(ocr_data)

        return ocr_regions

    @requires_dependencies("unstructured_inference")
    def get_layout_elements_from_image(
        self, image: PILImage, ocr_languages: str = "eng",
        clarifai_ocr_model: Optional[str] = None,
    ) -> List["LayoutElement"]:
        from unstructured.partition.pdf_image.inference_utils import build_layout_element
        if not clarifai_ocr_model:
            clarifai_ocr_model = OCR_DEFAULT_CLARIFAI_MODEL_URL
        ocr_regions = self.get_layout_from_image(
            image,
            ocr_languages=ocr_languages,
            clarifai_model_url=clarifai_ocr_model,
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
    def parse_data(self, ocr_data, zoom: float = 1) -> List["TextRegion"]:
        """
        Parse the OCR result data to extract a list of TextRegion objects from
        tesseract.

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
        - List[TextRegion]:
            A list of TextRegion objects, each representing a detected text region
            within the OCR-ed image.

        Note:
        - An empty string or a None value for the 'text' key in the input
          data frame will result in its associated bounding box being ignored.
        """

        from unstructured.partition.pdf_image.inference_utils import build_text_region_from_coords

        text_regions = []
        #add try catch block
        for data in ocr_data.outputs[0].data.regions:
            x1 = data.region_info.bounding_box.top_row
            y1 = data.region_info.bounding_box.left_col
            x2 = data.region_info.bounding_box.bottom_row
            y2 = data.region_info.bounding_box.right_col
            text_region = build_text_region_from_coords(
                x1,
                y1,
                x2,
                y2,
                text=data.data.text.raw,
                source=Source.OCR_CLARIFAI,
            )
            text_regions.append(text_region)

        return text_regions

    def image_to_byte_array(self, image: PILImage) -> bytes:
        import io
        # BytesIO is a file-like buffer stored in memory
        imgByteArr = io.BytesIO()
        # image.save expects a file-like as a argument
        image.save(imgByteArr, format=image.format)
        # Turn the BytesIO object back into a bytes object
        imgByteArr = imgByteArr.getvalue()
        return imgByteArr

    def pil_image_to_bytes(self, image: PILImage) -> bytes:
        from io import BytesIO
        with BytesIO() as output:
            image.save(output, format="PNG")
            return output.getvalue()