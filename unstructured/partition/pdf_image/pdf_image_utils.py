from __future__ import annotations

import base64
import os
import re
import tempfile
import unicodedata
from copy import deepcopy
from io import BytesIO
from pathlib import Path, PurePath
from typing import IO, TYPE_CHECKING, BinaryIO, Iterator, List, Optional, Tuple, Union, cast

import cv2
import numpy as np
import pdf2image
from PIL import Image

from unstructured.documents.elements import ElementType
from unstructured.logger import logger
from unstructured.partition.common import (
    convert_to_bytes,
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.partition.utils.config import env_config

if TYPE_CHECKING:
    from unstructured_inference.inference.layout import DocumentLayout, PageLayout, TextRegion
    from unstructured_inference.inference.layoutelement import LayoutElement

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


def pad_element_bboxes(
    element: "LayoutElement",
    padding: Union[int, float],
) -> "LayoutElement":
    """Increases (or decreases, if padding is negative) the size of the bounding
    boxes of the element by extending the boundary outward (resp. inward)"""

    out_element = deepcopy(element)
    out_element.bbox.x1 -= padding
    out_element.bbox.x2 += padding
    out_element.bbox.y1 -= padding
    out_element.bbox.y2 += padding

    return out_element


def pad_bbox(
    bbox: Tuple[float, float, float, float],
    padding: Tuple[Union[int, float], Union[int, float]],
) -> Tuple[float, float, float, float]:
    """Pads a bounding box (bbox) by a specified horizontal and vertical padding."""

    x1, y1, x2, y2 = bbox
    h_padding, v_padding = padding
    x1 -= h_padding
    x2 += h_padding
    y1 -= v_padding
    y2 += v_padding

    return x1, y1, x2, y2


def save_elements(
    elements: List["Element"],
    element_category_to_save: str,
    pdf_image_dpi: int,
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO]] = None,
    is_image: bool = False,
    extract_image_block_to_payload: bool = False,
    output_dir_path: Optional[str] = None,
):
    """
    Saves specific elements from a PDF as images either to a directory or embeds them in the
    element's payload.

    This function processes a list of elements partitioned from a PDF file. For each element of
    a specified category, it extracts and saves the image. The images can either be saved to
    a specified directory or embedded into the element's payload as a base64-encoded string.
    """

    if not output_dir_path:
        if env_config.GLOBAL_WORKING_DIR_ENABLED:
            output_dir_path = str(Path(env_config.GLOBAL_WORKING_PROCESS_DIR) / "figures")
        else:
            output_dir_path = str(Path.cwd() / "figures")
    os.makedirs(output_dir_path, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        if is_image:
            if file is None:
                image_paths = [filename]
            else:
                if hasattr(file, "seek"):
                    file.seek(0)
                temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir)
                temp_file.write(file.read() if hasattr(file, "read") else file)
                temp_file.flush()
                image_paths = [temp_file.name]
        else:
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
            h_padding = env_config.EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD
            v_padding = env_config.EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD
            padded_bbox = cast(
                Tuple[int, int, int, int], pad_bbox((x1, y1, x2, y2), (h_padding, v_padding))
            )
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
                cropped_image = image.crop(padded_bbox)
                if extract_image_block_to_payload:
                    buffered = BytesIO()
                    cropped_image.save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue())
                    img_base64_str = img_base64.decode()
                    el.metadata.image_base64 = img_base64_str
                    el.metadata.image_mime_type = "image/jpeg"
                else:
                    write_image(cropped_image, output_f_path)
                    # add image path to element metadata
                    el.metadata.image_path = output_f_path
            except (ValueError, IOError):
                logger.warning("Image Extraction Error: Skipping the failed image", exc_info=True)


def check_element_types_to_extract(
    extract_image_block_types: Optional[List[str]],
) -> List[str]:
    """Check and normalize the provided list of element types to extract."""

    if extract_image_block_types is None:
        return []

    if not isinstance(extract_image_block_types, list):
        raise TypeError(
            "The extract_image_block_types parameter must be a list of element types as strings, "
            "ex. ['Table', 'Image']",
        )

    available_element_types = list(ElementType.to_dict().values())
    normalized_extract_image_block_types = []
    for el_type in extract_image_block_types:
        normalized_el_type = el_type.lower().capitalize()
        if normalized_el_type not in available_element_types:
            logger.warning(f"The requested type ({el_type}) doesn't match any available type")
        normalized_extract_image_block_types.append(normalized_el_type)

    return normalized_extract_image_block_types


def valid_text(text: str) -> bool:
    """a helper that determines if the text is valid ascii text"""
    if not text:
        return False
    return "(cid:" not in text


def cid_ratio(text: str) -> float:
    """Gets ratio of unknown 'cid' characters extracted from text to all characters."""
    if not is_cid_present(text):
        return 0.0
    cid_pattern = r"\(cid\:(\d+)\)"
    unmatched, n_cid = re.subn(cid_pattern, "", text)
    total = n_cid + len(unmatched)
    return n_cid / total


def is_cid_present(text: str) -> bool:
    """Checks if a cid code is present in a text selection."""
    if len(text) < len("(cid:x)"):
        return False
    return text.find("(cid:") != -1


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


def convert_pdf_to_images(
    filename: str = "",
    file: Optional[bytes | IO[bytes]] = None,
    chunk_size: int = 10,
) -> Iterator[Image.Image]:
    # Convert a PDF in small chunks of pages at a time (e.g. 1-10, 11-20... and so on)
    exactly_one(filename=filename, file=file)
    if file is not None:
        f_bytes = convert_to_bytes(file)
        info = pdf2image.pdfinfo_from_bytes(f_bytes)
    else:
        f_bytes = None
        info = pdf2image.pdfinfo_from_path(filename)

    total_pages = info["Pages"]
    for start_page in range(1, total_pages + 1, chunk_size):
        end_page = min(start_page + chunk_size - 1, total_pages)
        if f_bytes is not None:
            chunk_images = pdf2image.convert_from_bytes(
                f_bytes,
                first_page=start_page,
                last_page=end_page,
            )
        else:
            chunk_images = pdf2image.convert_from_path(
                filename,
                first_page=start_page,
                last_page=end_page,
            )

        for image in chunk_images:
            yield image


def get_the_last_modification_date_pdf_or_img(
    file: Optional[bytes | IO[bytes]] = None,
    filename: Optional[str] = "",
    date_from_file_object: bool = False,
) -> str | None:
    last_modification_date = None
    if not file and filename:
        last_modification_date = get_last_modified_date(filename=filename)
    elif not filename and file:
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )
    return last_modification_date


def remove_control_characters(text: str) -> str:
    """Removes control characters from text."""

    # Replace newline character with a space
    text = text.replace("\t", " ").replace("\n", " ")
    # Remove other control characters
    out_text = "".join(c for c in text if unicodedata.category(c)[0] != "C")
    return out_text
