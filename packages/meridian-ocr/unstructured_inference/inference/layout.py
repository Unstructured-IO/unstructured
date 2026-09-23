from __future__ import annotations

import os
import tempfile
from functools import cached_property
from pathlib import PurePath
from typing import Any, BinaryIO, Collection, List, Optional, Union, cast

import numpy as np
from PIL import Image, ImageSequence

from unstructured_inference.inference import pdf_image as pdf_image_utils
from unstructured_inference.inference.elements import (
    TextRegion,
)
from unstructured_inference.inference.layoutelement import LayoutElement, LayoutElements
from unstructured_inference.logger import logger
from unstructured_inference.models.base import get_model
from unstructured_inference.models.unstructuredmodel import (
    UnstructuredElementExtractionModel,
    UnstructuredObjectDetectionModel,
)
from unstructured_inference.visualize import draw_bbox

convert_pdf_to_image = pdf_image_utils.convert_pdf_to_image
_pdfium_lock = pdf_image_utils._pdfium_lock


class DocumentLayout:
    """Class for handling documents that are saved as .pdf files. For .pdf files, a
    document image analysis (DIA) model detects the layout of the page prior to extracting
    element."""

    def __init__(self, pages=None):
        self._pages = pages

    def __str__(self) -> str:
        return "\n\n".join([str(page) for page in self.pages])

    @property
    def pages(self) -> List[PageLayout]:
        """Gets all elements from pages in sequential order."""
        return self._pages

    @classmethod
    def from_pages(cls, pages: List[PageLayout]) -> DocumentLayout:
        """Generates a new instance of the class from a list of `PageLayouts`s"""
        doc_layout = cls()
        doc_layout._pages = pages
        return doc_layout

    @classmethod
    def from_file(
        cls,
        filename: str,
        fixed_layouts: Optional[List[Optional[List[TextRegion]]]] = None,
        pdf_image_dpi: int = 200,
        pdf_render_max_pixels_per_page: Optional[int] = None,
        password: Optional[str] = None,
        **kwargs,
    ) -> DocumentLayout:
        """Creates a DocumentLayout from a pdf file."""
        logger.info(f"Reading PDF for file: {filename} ...")

        with tempfile.TemporaryDirectory() as temp_dir:
            _image_paths = convert_pdf_to_image(
                filename=filename,
                dpi=pdf_image_dpi,
                output_folder=temp_dir,
                path_only=True,
                password=password,
                pdf_render_max_pixels_per_page=pdf_render_max_pixels_per_page,
            )
            image_paths = cast(List[str], _image_paths)
            number_of_pages = len(image_paths)
            pages: List[PageLayout] = []
            if fixed_layouts is None:
                fixed_layouts = [None for _ in range(0, number_of_pages)]
            for i, (image_path, fixed_layout) in enumerate(zip(image_paths, fixed_layouts)):
                # NOTE(robinson) - In the future, maybe we detect the page number and default
                # to the index if it is not detected
                with Image.open(image_path) as image:
                    page = PageLayout.from_image(
                        image,
                        number=i + 1,
                        document_filename=filename,
                        fixed_layout=fixed_layout,
                        pdf_render_max_pixels_per_page=pdf_render_max_pixels_per_page,
                        **kwargs,
                    )
                    pages.append(page)
            return cls.from_pages(pages)

    @classmethod
    def from_image_file(
        cls,
        filename: str,
        detection_model: Optional[UnstructuredObjectDetectionModel] = None,
        element_extraction_model: Optional[UnstructuredElementExtractionModel] = None,
        fixed_layout: Optional[List[TextRegion]] = None,
        **kwargs,
    ) -> DocumentLayout:
        """Creates a DocumentLayout from an image file."""
        logger.info(f"Reading image file: {filename} ...")
        try:
            image = Image.open(filename)
            format = image.format
            images: list[Image.Image] = []
            for i, im in enumerate(ImageSequence.Iterator(image)):
                im = im.convert("RGB")
                im.format = format
                images.append(im)
        except Exception as e:
            if os.path.isdir(filename) or os.path.isfile(filename):
                raise e
            else:
                raise FileNotFoundError(f'File "{filename}" not found!') from e
        pages = []
        for i, image in enumerate(images):  # type: ignore
            page = PageLayout.from_image(
                image,
                image_path=filename,
                number=i,
                detection_model=detection_model,
                element_extraction_model=element_extraction_model,
                fixed_layout=fixed_layout,
                **kwargs,
            )
            pages.append(page)
        return cls.from_pages(pages)


class PageLayout:
    """Class for an individual PDF page."""

    def __init__(
        self,
        number: int,
        image: Image.Image,
        image_metadata: Optional[dict] = None,
        image_path: Optional[Union[str, PurePath]] = None,  # TODO: Deprecate
        document_filename: Optional[Union[str, PurePath]] = None,
        detection_model: Optional[UnstructuredObjectDetectionModel] = None,
        element_extraction_model: Optional[UnstructuredElementExtractionModel] = None,
        pdf_render_max_pixels_per_page: Optional[int] = None,
        password: Optional[str] = None,
    ):
        if detection_model is not None and element_extraction_model is not None:
            raise ValueError("Only one of detection_model and extraction_model should be passed.")
        self.image: Optional[Image.Image] = image
        if image_metadata is None:
            image_metadata = {}
        self.image_metadata = image_metadata
        self.image_path = image_path
        self.image_array: Union[np.ndarray[Any, Any], None] = None
        self.document_filename = document_filename
        self.number = number
        self.detection_model = detection_model
        self.element_extraction_model = element_extraction_model
        self.pdf_render_max_pixels_per_page = pdf_render_max_pixels_per_page
        self.elements_array: LayoutElements | None = None
        self.password = password
        # NOTE(alan): Dropped LocationlessLayoutElement that was created for chipper - chipper has
        # locations now and if we need to support LayoutElements without bounding boxes we can make
        # the bbox property optional

    def __str__(self) -> str:
        return "\n\n".join([str(element) for element in self.elements])

    @cached_property
    def elements(self) -> Collection[LayoutElement]:
        """return a list of layout elements from the array data structure; intended for backward
        compatibility"""
        if self.elements_array is None:
            return []
        return self.elements_array.as_list()

    def get_elements_using_image_extraction(
        self,
        inplace=True,
    ) -> Optional[list[LayoutElement]]:
        """Uses end-to-end text element extraction model to extract the elements on the page."""
        if self.element_extraction_model is None:
            raise ValueError(
                "Cannot get elements using image extraction, no image extraction model defined",
            )
        assert self.image is not None
        elements = self.element_extraction_model(self.image)
        if inplace:
            self.elements = elements
            return None
        return elements

    def get_elements_with_detection_model(
        self,
        inplace: bool = True,
    ) -> Optional[LayoutElements]:
        """Uses specified model to detect the elements on the page."""
        if self.detection_model is None:
            model = get_model()
            if isinstance(model, UnstructuredObjectDetectionModel):
                self.detection_model = model
            else:
                raise NotImplementedError("Default model should be a detection model")

        # NOTE(mrobinson) - We'll want make this model inference step some kind of
        # remote call in the future.
        assert self.image is not None
        inferred_layout: LayoutElements = self.detection_model(self.image)
        routing = inferred_layout.routing
        routing_score = inferred_layout.routing_score
        inferred_layout = self.detection_model.deduplicate_detected_elements(
            inferred_layout,
        )
        inferred_layout.routing = routing
        inferred_layout.routing_score = routing_score

        if inplace:
            self.elements_array = inferred_layout
            return None

        return inferred_layout

    def _get_image_array(self) -> Union[np.ndarray[Any, Any], None]:
        """Converts the raw image into a numpy array."""
        if self.image_array is None:
            if self.image:
                self.image_array = np.array(self.image)
            else:
                image = Image.open(self.image_path)  # type: ignore
                self.image_array = np.array(image)
        return self.image_array

    def annotate(
        self,
        colors: Optional[Union[List[str], str]] = None,
        image_dpi: int = 200,
        annotation_data: Optional[dict[str, dict]] = None,
        add_details: bool = False,
        sources: Optional[List[str]] = None,
    ) -> Image.Image:
        """Annotates the elements on the page image.
        if add_details is True, and the elements contain type and source attributes, then
        the type and source will be added to the image.
        sources is a list of sources to annotate. If sources is ["all"], then all sources will be
        annotated. Current sources allowed are "yolox","detectron2_onnx" and "detectron2_lp" """
        if colors is None:
            colors = ["red" for _ in self.elements]
        if isinstance(colors, str):
            colors = [colors]
        # If there aren't enough colors, just cycle through the colors a few times
        if len(colors) < len(self.elements):
            n_copies = (len(self.elements) // len(colors)) + 1
            colors = colors * n_copies

        # Hotload image if it hasn't been loaded yet
        if self.image:
            img = self.image.copy()
        elif self.image_path:
            img = Image.open(self.image_path)
        else:
            img = self._get_image(self.document_filename, self.number, image_dpi)

        if annotation_data is None:
            for el, color in zip(self.elements, colors):
                if sources is None or el.source in sources:
                    img = draw_bbox(img, el, color=color, details=add_details)
        else:
            for attribute, style in annotation_data.items():
                if hasattr(self, attribute) and getattr(self, attribute):
                    color = style["color"]
                    width = style["width"]
                    for region in getattr(self, attribute):
                        required_source = getattr(region, "source", None)
                        if (sources is None) or (required_source in sources):
                            img = draw_bbox(
                                img,
                                region,
                                color=color,
                                width=width,
                                details=add_details,
                            )

        return img

    def _get_image(self, filename, page_number, pdf_image_dpi: int = 200) -> Image.Image:
        """Hotloads a page image from a pdf file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            _image_paths = convert_pdf_to_image(
                filename=filename,
                dpi=pdf_image_dpi,
                output_folder=temp_dir,
                path_only=True,
                pdf_render_max_pixels_per_page=self.pdf_render_max_pixels_per_page,
            )
            image_paths = cast(List[str], _image_paths)
            if page_number > len(image_paths):
                raise ValueError(
                    f"Page number {page_number} is greater than the number of pages in the PDF.",
                )

            with Image.open(image_paths[page_number - 1]) as image:
                return image.copy()

    @classmethod
    def from_image(
        cls,
        image: Image.Image,
        image_path: Optional[Union[str, PurePath]] = None,
        document_filename: Optional[Union[str, PurePath]] = None,
        number: int = 1,
        detection_model: Optional[UnstructuredObjectDetectionModel] = None,
        element_extraction_model: Optional[UnstructuredElementExtractionModel] = None,
        fixed_layout: Optional[List[TextRegion]] = None,
        pdf_render_max_pixels_per_page: Optional[int] = None,
    ):
        """Creates a PageLayout from an already-loaded PIL Image."""

        page = cls(
            number=number,
            image=image,
            detection_model=detection_model,
            element_extraction_model=element_extraction_model,
            pdf_render_max_pixels_per_page=pdf_render_max_pixels_per_page,
        )
        # FIXME (yao): refactor the other methods so they all return elements like the third route
        if page.element_extraction_model is not None:
            page.get_elements_using_image_extraction()
        elif fixed_layout is None:
            page.get_elements_with_detection_model()
        else:
            page.elements = []

        page.image_metadata = {
            "format": page.image.format if page.image else None,
            "width": page.image.width if page.image else None,
            "height": page.image.height if page.image else None,
            "pdf_rotation": int(page.image.info.get("pdf_rotation", 0)) if page.image else 0,
            "pdf_rotation_correction": (
                int(page.image.info.get("pdf_rotation_correction", 0)) if page.image else 0
            ),
        }
        page.image_path = os.path.abspath(image_path) if image_path else None
        page.document_filename = os.path.abspath(document_filename) if document_filename else None

        # Clear the image to save memory
        page.image = None

        return page


def process_data_with_model(
    data: BinaryIO,
    model_name: Optional[str],
    password: Optional[str] = None,
    **kwargs: Any,
) -> DocumentLayout:
    """Process PDF or image as file-like object `data` into a `DocumentLayout`.

    Uses the model identified by `model_name`.
    """
    # Note: We use a temp dir, not a temp file,
    # because the latter fails on Windows
    # https://github.com/Unstructured-IO/unstructured-inference/pull/376
    with tempfile.TemporaryDirectory() as tmp_dir_path:
        file_path = os.path.join(tmp_dir_path, "document")
        with open(file_path, "wb") as f:
            f.write(data.read())
            f.flush()
        layout = process_file_with_model(
            file_path,
            model_name,
            password=password,
            **kwargs,
        )

    return layout


def process_file_with_model(
    filename: str,
    model_name: Optional[str],
    is_image: bool = False,
    fixed_layouts: Optional[List[Optional[List[TextRegion]]]] = None,
    pdf_image_dpi: int = 200,
    pdf_render_max_pixels_per_page: Optional[int] = None,
    password: Optional[str] = None,
    **kwargs: Any,
) -> DocumentLayout:
    """Processes pdf or image file with name filename into a DocumentLayout by using
    a model identified by model_name."""

    model = get_model(model_name, **kwargs)
    if isinstance(model, UnstructuredObjectDetectionModel):
        detection_model = model
        element_extraction_model = None
    elif isinstance(model, UnstructuredElementExtractionModel):
        detection_model = None
        element_extraction_model = model
    else:
        raise ValueError(f"Unsupported model type: {type(model)}")
    layout = (
        DocumentLayout.from_image_file(
            filename,
            detection_model=detection_model,
            element_extraction_model=element_extraction_model,
            **kwargs,
        )
        if is_image
        else DocumentLayout.from_file(
            filename,
            detection_model=detection_model,
            element_extraction_model=element_extraction_model,
            fixed_layouts=fixed_layouts,
            pdf_image_dpi=pdf_image_dpi,
            pdf_render_max_pixels_per_page=pdf_render_max_pixels_per_page,
            password=password,
            **kwargs,
        )
    )
    return layout
