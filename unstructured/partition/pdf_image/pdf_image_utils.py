import os
import tempfile
from pathlib import PurePath
from typing import TYPE_CHECKING, BinaryIO, List, Optional, Union, cast

import cv2
import numpy as np
import pdf2image
from PIL import Image

from unstructured.documents.elements import ElementType
from unstructured.logger import logger
from unstructured.partition.common import convert_to_bytes

if TYPE_CHECKING:
    from unstructured.documents.elements import Element


def write_image(image: Union[Image.Image, np.ndarray], output_image_path: str):
    """
    Write an image to a specified file path, supporting both PIL Image and numpy ndarray formats.

    Parameters:
    - image (Union[Image.Image, np.ndarray]): The image to be written, which can be in PIL Image
      format or a numpy ndarray format.
    - output_image_path (str): The path to which the image will be written.

    Raises:
    - ValueError: If the provided image type is neither PIL Image nor numpy ndarray.

    Returns:
    - None: The function writes the image to the specified path but does not return any value.
    """

    if isinstance(image, Image.Image):
        image.save(output_image_path)
    elif isinstance(image, np.ndarray):
        cv2.imwrite(output_image_path, image)
    else:
        raise ValueError("Unsupported Image Type")


def convert_pdf_to_image(
    filename: str,
    file: Optional[Union[bytes, BinaryIO]] = None,
    dpi: int = 200,
    output_folder: Optional[Union[str, PurePath]] = None,
    path_only: bool = False,
) -> Union[List[Image.Image], List[str]]:
    """Get the image renderings of the pdf pages using pdf2image"""

    if path_only and not output_folder:
        raise ValueError("output_folder must be specified if path_only is true")

    if file is not None:
        f_bytes = convert_to_bytes(file)
        images = pdf2image.convert_from_bytes(
            f_bytes,
            dpi=dpi,
            output_folder=output_folder,
            paths_only=path_only,
        )
    else:
        images = pdf2image.convert_from_path(
            filename,
            dpi=dpi,
            output_folder=output_folder,
            paths_only=path_only,
        )

    return images


def save_elements(
    elements: List["Element"],
    element_category_to_save: str,
    pdf_image_dpi: int,
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO]] = None,
    output_dir_path: Optional[str] = None,
):
    """
    Extract and save images from the page. This method iterates through the layout elements
    of the page, identifies image regions, and extracts and saves them as separate image files.
    """

    if not output_dir_path:
        output_dir_path = os.path.join(os.getcwd(), "figures")
    os.makedirs(output_dir_path, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        _image_paths = convert_pdf_to_image(
            filename,
            file,
            pdf_image_dpi,
            output_folder=temp_dir,
            path_only=True,
        )
        image_paths = cast(List[str], _image_paths)

        figure_number = 0
        for el in elements:
            if el.category != element_category_to_save:
                continue

            coordinates = el.metadata.coordinates
            if not coordinates or not coordinates.points:
                continue

            points = coordinates.points
            x1, y1 = points[0]
            x2, y2 = points[2]
            page_number = el.metadata.page_number

            figure_number += 1
            try:
                basename = "table" if el.category == ElementType.TABLE else "figure"
                output_f_path = os.path.join(
                    output_dir_path,
                    f"{basename}-{page_number}-{figure_number}.jpg",
                )
                image_path = image_paths[page_number - 1]
                image = Image.open(image_path)
                cropped_image = image.crop((x1, y1, x2, y2))
                write_image(cropped_image, output_f_path)
                # add image path to element metadata
                el.metadata.image_path = output_f_path
            except (ValueError, IOError):
                logger.warning("Image Extraction Error: Skipping the failed image", exc_info=True)


def check_element_types_to_extract(
    extract_element_types: Optional[List[str]],
) -> List[str]:
    """Check and normalize the provided list of element types to extract."""

    if extract_element_types is None:
        return []

    if not isinstance(extract_element_types, list):
        raise TypeError(
            "The extract_element_types parameter must be a list of element types as strings, "
            "ex. ['Table', 'Image']",
        )

    available_element_types = list(ElementType.to_dict().values())
    normalized_extract_element_types = []
    for el_type in extract_element_types:
        normalized_el_type = el_type.lower().capitalize()
        if normalized_el_type not in available_element_types:
            logger.warning(f"The requested type ({el_type}) doesn't match any available type")
        normalized_extract_element_types.append(normalized_el_type)

    return normalized_extract_element_types


def valid_text(text: str) -> bool:
    """a helper that determines if the text is valid ascii text"""
    if not text:
        return False
    return "(cid:" not in text
