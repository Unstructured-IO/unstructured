from typing import BinaryIO, Dict, List, Optional, cast

from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.utils import open_filename

from unstructured.file_utils.filetype import FileType
from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.utils import dependency_exists

VALID_STRATEGIES: Dict[str, List[FileType]] = {
    "hi_res": [
        FileType.PDF,
        FileType.JPG,
        FileType.PNG,
    ],
    "ocr_only": [
        FileType.PDF,
        FileType.JPG,
        FileType.PNG,
    ],
    "fast": [
        FileType.PDF,
    ],
}


def validate_strategy(strategy: str, filetype: FileType):
    """Determines if the strategy is valid for the specified filetype."""
    valid_filetypes = VALID_STRATEGIES.get(strategy, None)
    if valid_filetypes is None:
        raise ValueError(f"{strategy} is not a valid strategy.")
    if filetype not in valid_filetypes:
        raise ValueError(f"{strategy} is not a valid strategy for filetype {filetype}.")


def is_pdf_text_extractable(filename: str = "", file: Optional[bytes] = None):
    """Checks to see if the text from a PDF document is extractable. Sometimes the
    text is not extractable due to PDF security settings."""
    exactly_one(filename=filename, file=file)

    def _fp_is_extractable(fp):
        try:
            next(PDFPage.get_pages(fp, check_extractable=True))
            extractable = True
        except PDFTextExtractionNotAllowed:
            extractable = False
        return extractable

    if filename:
        with open_filename(filename, "rb") as fp:
            fp = cast(BinaryIO, fp)
            return _fp_is_extractable(fp)
    elif file:
        fp = cast(BinaryIO, file)
        return _fp_is_extractable(fp)


def determine_pdf_or_image_strategy(
    strategy: str,
    filename: str = "",
    file: Optional[bytes] = None,
    is_image: bool = False,
):
    """Determines what strategy to use for processing PDFs or images, accounting for fallback
    logic if some dependencies are not available."""
    detectron2_installed = dependency_exists("detectron2")
    if is_image:
        pdf_text_extractable = False
    else:
        pdf_text_extractable = is_pdf_text_extractable(filename=filename, file=file)

    if file is not None:
        file.seek(0)  # type: ignore

    if not detectron2_installed and not pdf_text_extractable:
        raise ValueError(
            "detectron2 is not installed and the text of the PDF is not extractable. "
            "To process this file, install detectron2 or remove copy protection from the PDF.",
        )

    if not pdf_text_extractable:
        if strategy == "fast":
            logger.warning(
                "PDF text is not extractable. Cannot use the fast partitioning "
                "strategy. Falling back to partitioning with the hi_res strategy.",
            )
        return "hi_res"

    if not detectron2_installed:
        if strategy == "hi_res":
            logger.warning(
                "detectron2 is not installed. Cannot use the hi_res partitioning "
                "strategy. Falling back to partitioning with the fast strategy.",
            )
        return "fast"

    if not pdf_text_extractable:
        if strategy == "fast":
            logger.warning(
                "PDF text is not extractable. Cannot use the fast partitioning "
                "strategy. Falling back to partitioning with the hi_res strategy.",
            )
        return "hi_res"

    return strategy
