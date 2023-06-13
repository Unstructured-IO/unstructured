from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Dict, List, Optional, Union, cast

from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.utils import open_filename

from unstructured.logger import logger
from unstructured.partition.common import exactly_one
from unstructured.utils import dependency_exists

VALID_STRATEGIES: Dict[str, List[str]] = {
    "auto": [
        "pdf",
        "image",
    ],
    "hi_res": [
        "pdf",
        "image",
    ],
    "ocr_only": [
        "pdf",
        "image",
    ],
    "fast": [
        "pdf",
    ],
}


def validate_strategy(strategy: str, filetype: str):
    """Determines if the strategy is valid for the specified filetype."""
    valid_filetypes = VALID_STRATEGIES.get(strategy, None)
    if valid_filetypes is None:
        raise ValueError(f"{strategy} is not a valid strategy.")
    if filetype not in valid_filetypes:
        raise ValueError(f"{strategy} is not a valid strategy for filetype {filetype}.")


def is_pdf_text_extractable(
    filename: str = "",
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
):
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
    file: Optional[Union[bytes, BinaryIO, SpooledTemporaryFile]] = None,
    is_image: bool = False,
    infer_table_structure: bool = False,
):
    """Determines what strategy to use for processing PDFs or images, accounting for fallback
    logic if some dependencies are not available."""
    pytesseract_installed = dependency_exists("pytesseract")
    unstructured_inference_installed = dependency_exists("unstructured_inference")

    if is_image:
        # Note(yuming): There is no fast strategy for images,
        # use ocr_only as a fallback plan for consistency with PDFs.
        # This can be removed once unstructured-api use auto as the default strategy.
        if strategy == "fast":
            strategy = "ocr_only"
        validate_strategy(strategy, "image")
        pdf_text_extractable = False
    else:
        validate_strategy(strategy, "pdf")
        pdf_text_extractable = is_pdf_text_extractable(filename=filename, file=file)

    if strategy == "auto":
        if is_image:
            strategy = _determine_image_auto_strategy(infer_table_structure=infer_table_structure)
        else:
            strategy = _determine_pdf_auto_strategy(
                pdf_text_extractable=pdf_text_extractable,
                infer_table_structure=infer_table_structure,
            )

    if file is not None:
        file.seek(0)  # type: ignore

    if all(
        [not unstructured_inference_installed, not pytesseract_installed, not pdf_text_extractable],
    ):
        raise ValueError(
            "unstructured_inference is not installed, pytesseract is not installed "
            "and the text of the PDF is not extractable. "
            "To process this file, install unstructured_inference, install pytesseract, "
            "or remove copy protection from the PDF.",
        )

    if strategy == "fast" and not pdf_text_extractable:
        logger.warning(
            "PDF text is not extractable. Cannot use the fast partitioning "
            "strategy. Falling back to partitioning with the ocr_only strategy.",
        )
        # NOTE(robinson) - fallback to ocr_only here because it is faster than hi_res
        return "ocr_only"

    elif strategy == "hi_res" and not unstructured_inference_installed:
        logger.warning(
            "unstructured_inference is not installed. Cannot use the hi_res partitioning "
            "strategy. Falling back to partitioning with another strategy.",
        )
        # NOTE(robinson) - fallback to ocr_only if possible because it is the most
        # similar to hi_res
        if pytesseract_installed:
            logger.warning("Falling back to partitioning with ocr_only.")
            return "ocr_only"
        else:
            logger.warning("Falling back to partitioning with fast.")
            return "fast"

    elif strategy == "ocr_only" and not pytesseract_installed:
        logger.warning(
            "pytesseract is not installed. Cannot use the ocr_only partitioning "
            "strategy. Falling back to partitioning with another strategy.",
        )
        if pdf_text_extractable:
            logger.warning("Falling back to partitioning with fast.")
            return "fast"
        else:
            logger.warning("Falling back to partitioning with hi_res.")
            return "hi_res"

    return strategy


def _determine_image_auto_strategy(infer_table_structure: bool = False):
    """If "auto" is passed in as the strategy, determines what strategy to use
    for images."""
    if infer_table_structure is True:
        return "hi_res"
    else:
        return "ocr_only"


def _determine_pdf_auto_strategy(
    pdf_text_extractable: bool = True,
    infer_table_structure: bool = False,
):
    """If "auto" is passed in as the strategy, determines what strategy to use
    for PDFs."""
    # NOTE(robinson) - Currrently "hi_res" is the only stategy where
    # infer_table_structure is used.
    if infer_table_structure:
        return "hi_res"

    if pdf_text_extractable:
        return "fast"
    else:
        return "ocr_only"
