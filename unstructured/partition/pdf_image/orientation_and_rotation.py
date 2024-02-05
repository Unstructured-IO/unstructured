from __future__ import annotations

import io
from typing import BinaryIO, Literal, Optional, Union, cast

import pypdf
from PIL import Image as PILImage

from unstructured.partition.utils.constants import ReorientationStrategy
from unstructured.utils import requires_dependencies

FULL_CIRCLE = 360

RIGHT_ORIENTATIONS = [0, 90, 180, 270]
Orientation = Literal[0, 90, 180, 270]


@requires_dependencies("unstructured_pytesseract")
def _find_orientation_pytesseract(page: PILImage) -> Orientation:
    raise NotImplementedError("tesserocr-based page reorientation is not implemented.")


def _find_orientation_tesserocr(page: PILImage) -> Orientation:
    raise NotImplementedError("tesserocr-based page reorientation is not implemented.")


def _find_orientation_cnn(page: PILImage) -> Orientation:
    raise NotImplementedError("CNN-based page reorientation is not implemented.")


def _find_orientation(page: pypdf.PageObject, reorientation_strategy: str) -> Orientation:
    if len(page.images) != 1:
        # extremely unlikely to be a page scan, which is the only page type we want rotated
        return 0
    if reorientation_strategy == ReorientationStrategy.NONE:
        return 0

    image = PILImage.open(io.BytesIO(page.images[0].data))

    strategies = {
        ReorientationStrategy.PYTESSERACT: _find_orientation_pytesseract,
        ReorientationStrategy.CNN: _find_orientation_cnn,
        ReorientationStrategy.TESSEROCR: _find_orientation_tesserocr,
    }

    if reorientation_strategy not in strategies:
        raise ValueError(f"Unknown reorientation strategy picked: {reorientation_strategy}")

    image_orientation = strategies[reorientation_strategy](image)
    return cast(Orientation, (page.rotation + image_orientation) % FULL_CIRCLE)


def reorient_file_or_data(
    filename: str,
    file: Optional[Union[bytes, BinaryIO]],
    reorientation_strategy: str,
) -> io.BytesIO:
    """Opens the PDF, determines the orientation of individual pages,
       rotates as needed and writes the result to target.
    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    reorientation_strategy
        The strategy to use for detecting orientation.
        Valid strategies are governed by the ReorientationStrategy constant.
    target
        The writable (mode should be w+) file to save the converted pdf to.
        Allows simple use within with temptile.TemporaryFile closures.

    """
    reader = pypdf.PdfReader(file if file is not None else filename)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        orientation = _find_orientation(page, reorientation_strategy=reorientation_strategy)
        page = page.rotate(-orientation)
        writer.add_page(page)
    target = io.BytesIO()
    writer.write(target)
    target.seek(0)
    return target
