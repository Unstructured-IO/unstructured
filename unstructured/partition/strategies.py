from typing import List, Optional

from unstructured.logger import logger
from unstructured.partition.utils.constants import PartitionStrategy
from unstructured.utils import dependency_exists


def validate_strategy(strategy: str, is_image: bool = False):
    """Determines if the strategy is valid for the specified filetype."""

    valid_strategies = [
        PartitionStrategy.AUTO,
        PartitionStrategy.FAST,
        PartitionStrategy.OCR_ONLY,
        PartitionStrategy.HI_RES,
    ]
    if strategy not in valid_strategies:
        raise ValueError(f"{strategy} is not a valid strategy.")

    if strategy == PartitionStrategy.FAST and is_image:
        raise ValueError("The fast strategy is not available for image files.")


def determine_pdf_or_image_strategy(
    strategy: str,
    is_image: bool = False,
    pdf_text_extractable: bool = False,
    infer_table_structure: bool = False,
    extract_images_in_pdf: bool = False,
    extract_image_block_types: Optional[List[str]] = None,
):
    """Determines what strategy to use for processing PDFs or images, accounting for fallback
    logic if some dependencies are not available."""
    pytesseract_installed = dependency_exists("unstructured_pytesseract")
    unstructured_inference_installed = dependency_exists("unstructured_inference")

    if strategy == PartitionStrategy.AUTO:
        extract_element = extract_images_in_pdf or bool(extract_image_block_types)
        if is_image:
            strategy = _determine_image_auto_strategy()
        else:
            strategy = _determine_pdf_auto_strategy(
                pdf_text_extractable=pdf_text_extractable,
                infer_table_structure=infer_table_structure,
                extract_element=extract_element,
            )

    if all(
        [not unstructured_inference_installed, not pytesseract_installed, not pdf_text_extractable],
    ):
        raise ValueError(
            "unstructured_inference is not installed, pytesseract is not installed "
            "and the text of the PDF is not extractable. "
            "To process this file, install unstructured_inference, install pytesseract, "
            "or remove copy protection from the PDF.",
        )

    if strategy == PartitionStrategy.HI_RES and not unstructured_inference_installed:
        logger.warning(
            "unstructured_inference is not installed. Cannot use the hi_res partitioning "
            "strategy. Falling back to partitioning with another strategy.",
        )
        # NOTE(robinson) - fallback to ocr_only if possible because it is the most
        # similar to hi_res
        if pytesseract_installed:
            logger.warning("Falling back to partitioning with ocr_only.")
            return PartitionStrategy.OCR_ONLY
        else:
            logger.warning("Falling back to partitioning with fast.")
            return PartitionStrategy.FAST

    elif strategy == PartitionStrategy.OCR_ONLY and not pytesseract_installed:
        logger.warning(
            "pytesseract is not installed. Cannot use the ocr_only partitioning "
            "strategy. Falling back to partitioning with another strategy.",
        )
        if pdf_text_extractable:
            logger.warning("Falling back to partitioning with fast.")
            return PartitionStrategy.FAST
        else:
            logger.warning("Falling back to partitioning with hi_res.")
            return PartitionStrategy.HI_RES

    return strategy


def _determine_image_auto_strategy():
    """If "auto" is passed in as the strategy, determines what strategy to use
    for images."""
    # Use hi_res as the only default since images are only about one page
    return PartitionStrategy.HI_RES


def _determine_pdf_auto_strategy(
    pdf_text_extractable: bool = False,
    infer_table_structure: bool = False,
    extract_element: bool = False,
):
    """If "auto" is passed in as the strategy, determines what strategy to use
    for PDFs."""
    # NOTE(robinson) - Currently "hi_res" is the only strategy where
    # infer_table_structure and extract_images_in_pdf are used.
    if infer_table_structure or extract_element:
        return PartitionStrategy.HI_RES

    if pdf_text_extractable:
        return PartitionStrategy.FAST
    else:
        return PartitionStrategy.OCR_ONLY
