from typing import List, Optional

from unstructured.logger import logger
from unstructured.partition.utils.constants import (
    OCR_AGENT_GOOGLEVISION,
    OCR_AGENT_PADDLE,
    OCR_AGENT_TESSERACT,
    PartitionStrategy,
)
from unstructured.partition.utils.ocr_models.ocr_interface import OCRAgent
from unstructured.utils import dependency_exists


def _resolve_ocr_agent(ocr_agent: Optional[str] = None) -> str:
    return OCRAgent.get_configured_ocr_agent_module() if ocr_agent is None else ocr_agent


def _ocr_agent_installed(resolved_ocr_agent: str) -> bool:
    """Whether the runtime dependencies for `resolved_ocr_agent` are installed."""
    if not resolved_ocr_agent:
        return False
    if resolved_ocr_agent == OCR_AGENT_TESSERACT:
        return bool(dependency_exists("unstructured_pytesseract"))
    if resolved_ocr_agent == OCR_AGENT_PADDLE:
        return bool(dependency_exists("paddle") and dependency_exists("unstructured_paddleocr"))
    if resolved_ocr_agent == OCR_AGENT_GOOGLEVISION:
        return bool(dependency_exists("google.cloud.vision"))
    module_name = resolved_ocr_agent.rsplit(".", 1)[0]
    return bool(module_name and dependency_exists(module_name))


def _ocr_agent_dependency_label(resolved_ocr_agent: str) -> str:
    if resolved_ocr_agent == OCR_AGENT_TESSERACT or not resolved_ocr_agent:
        return "pytesseract"
    return resolved_ocr_agent


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
    ocr_agent: Optional[str] = None,
):
    """Determines what strategy to use for processing PDFs or images, accounting for fallback
    logic if some dependencies are not available."""
    resolved_ocr_agent = _resolve_ocr_agent(ocr_agent)
    ocr_installed = _ocr_agent_installed(resolved_ocr_agent)
    ocr_label = _ocr_agent_dependency_label(resolved_ocr_agent)
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
        [not unstructured_inference_installed, not ocr_installed, not pdf_text_extractable],
    ):
        raise ValueError(
            f"unstructured_inference is not installed, {ocr_label} is not installed "
            "and the text of the PDF is not extractable. "
            f"To process this file, install unstructured_inference, install {ocr_label}, "
            "or remove copy protection from the PDF.",
        )

    if strategy == PartitionStrategy.HI_RES and not unstructured_inference_installed:
        logger.warning(
            "unstructured_inference is not installed. Cannot use the hi_res partitioning "
            "strategy. Falling back to partitioning with another strategy.",
        )
        # NOTE(robinson) - fallback to ocr_only if possible because it is the most
        # similar to hi_res
        if ocr_installed:
            logger.warning("Falling back to partitioning with ocr_only.")
            return PartitionStrategy.OCR_ONLY
        else:
            logger.warning("Falling back to partitioning with fast.")
            return PartitionStrategy.FAST

    elif strategy == PartitionStrategy.OCR_ONLY and not ocr_installed:
        logger.warning(
            f"{ocr_label} is not installed. Cannot use the ocr_only partitioning "
            "strategy. Falling back to partitioning with another strategy.",
        )
        if pdf_text_extractable:
            logger.warning("Falling back to partitioning with fast.")
            return PartitionStrategy.FAST
        else:
            logger.warning("Falling back to partitioning with hi_res.")
            return PartitionStrategy.HI_RES

    return strategy


def pdf_strategy_can_resolve_to_fast(strategy: str, ocr_agent: Optional[str] = None) -> bool:
    """Whether `determine_pdf_or_image_strategy()` can resolve `strategy` to FAST for a PDF.

    FAST partitions a PDF from the elements of the up-front pdfminer pass, so those elements are
    needed only when this is True. `hi_res` falls back to FAST only when neither
    `unstructured_inference` nor the configured OCR agent is installed, and `ocr_only` only when
    the configured OCR agent is not installed.
    """
    if strategy == PartitionStrategy.HI_RES:
        return not dependency_exists("unstructured_inference") and not _ocr_agent_installed(
            _resolve_ocr_agent(ocr_agent)
        )
    if strategy == PartitionStrategy.OCR_ONLY:
        return not _ocr_agent_installed(_resolve_ocr_agent(ocr_agent))
    return True


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
