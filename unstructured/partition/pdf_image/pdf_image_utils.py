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
    from unstructured_inference.inference.layout import DocumentLayout, PageLayout, TextRegion

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


def annotate_layout_elements_with_image(
    inferred_page_layout: "PageLayout",
    extracted_page_layout: Optional["PageLayout"],
    output_dir_path: str,
    output_f_basename: str,
    page_number: int,
):
    """
     Annotates a page image with both inferred and extracted layout elements.

    This function takes the layout elements of a single page, either extracted from or inferred
    for the document, and annotates them on the page image. It creates two separate annotated
    images, one for each set of layout elements: 'inferred' and 'extracted'.
    These annotated images are saved to a specified directory.
    """

    layout_map = {"inferred": {"layout": inferred_page_layout, "color": "blue"}}
    if extracted_page_layout:
        layout_map["extracted"] = {"layout": extracted_page_layout, "color": "green"}

    for label, layout_data in layout_map.items():
        page_layout = layout_data.get("layout")
        color = layout_data.get("color")

        img = page_layout.annotate(colors=color)
        output_f_path = os.path.join(
            output_dir_path, f"{output_f_basename}_{page_number}_{label}.jpg"
        )
        write_image(img, output_f_path)
        print(f"output_image_path: {output_f_path}")


def annotate_layout_elements(
    inferred_document_layout: "DocumentLayout",
    extracted_layout: List["TextRegion"],
    filename: str,
    output_dir_path: str,
    pdf_image_dpi: int,
    is_image: bool = False,
) -> None:
    """
    Annotates layout elements on images extracted from a PDF or an image file.

    This function processes a given document (PDF or image) and annotates layout elements based
    on the inferred and extracted layout information.
    It handles both PDF documents and standalone image files. For PDFs, it converts each page
    into an image, whereas for image files, it processes the single image.
    """

    from unstructured_inference.inference.layout import PageLayout

    output_f_basename = os.path.splitext(os.path.basename(filename))[0]
    images = []
    try:
        if is_image:
            with Image.open(filename) as img:
                img = img.convert("RGB")
                images.append(img)

                extracted_page_layout = None
                if extracted_layout:
                    extracted_page_layout = PageLayout(
                        number=1,
                        image=img,
                    )
                    extracted_page_layout.elements = extracted_layout[0]

                inferred_page_layout = inferred_document_layout.pages[0]
                inferred_page_layout.image = img

                annotate_layout_elements_with_image(
                    inferred_page_layout=inferred_document_layout.pages[0],
                    extracted_page_layout=extracted_page_layout,
                    output_dir_path=output_dir_path,
                    output_f_basename=output_f_basename,
                    page_number=1,
                )
        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                _image_paths = pdf2image.convert_from_path(
                    filename,
                    dpi=pdf_image_dpi,
                    output_folder=temp_dir,
                    paths_only=True,
                )
                image_paths = cast(List[str], _image_paths)
                for i, image_path in enumerate(image_paths):
                    with Image.open(image_path) as img:
                        page_number = i + 1

                        extracted_page_layout = None
                        if extracted_layout:
                            extracted_page_layout = PageLayout(
                                number=page_number,
                                image=img,
                            )
                            extracted_page_layout.elements = extracted_layout[i]

                        inferred_page_layout = inferred_document_layout.pages[i]
                        inferred_page_layout.image = img

                        annotate_layout_elements_with_image(
                            inferred_page_layout=inferred_document_layout.pages[i],
                            extracted_page_layout=extracted_page_layout,
                            output_dir_path=output_dir_path,
                            output_f_basename=output_f_basename,
                            page_number=page_number,
                        )
    except Exception as e:
        if os.path.isdir(filename) or os.path.isfile(filename):
            raise e
        else:
            raise FileNotFoundError(f'File "{filename}" not found!') from e
