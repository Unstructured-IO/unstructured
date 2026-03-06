"""Utilities for detecting hierarchical heading levels in PDF documents.

This module infers heading levels (H1–H6) for PDF documents by analyzing:
1. PDF document outline/bookmarks
2. Document-order fallback when outline is unavailable
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Union

from pypdf import PdfReader

from unstructured.documents.elements import Element, Title
from unstructured.logger import logger

# Type for file argument: path (str), bytes, or file-like (BytesIO/IO[bytes])
_FileSource = Union[str, bytes, io.BytesIO, "io.IO[bytes]"]

# Outline entry: 1-based page number to match partitioner's element.metadata.page_number
OUTLINE_PAGE_ONE_BASED = True


def _clamp_heading_level(level: int) -> int:
    """Ensure heading level is in valid range 1-6."""
    return min(max(level, 1), 6)


def extract_pdf_outline(
    filename: Optional[str] = None,
    file: Optional[Union[bytes, io.BytesIO, "io.IO[bytes]"]] = None,
) -> list[dict[str, Any]]:
    """Extract PDF outline/bookmarks structure.

    Returns outline entries with 'title', 'level', and 'page'. Page numbers are
    1-based to match element.metadata.page_number from the partitioner.

    Args:
        filename: Path to PDF file
        file: File-like object or bytes containing PDF content

    Returns:
        List of outline entries with 'title', 'level', and 'page' (1-based) information
    """
    result: List[dict[str, Any]] = []

    try:
        if filename:
            reader = PdfReader(filename)
        elif file:
            if isinstance(file, bytes):
                file = io.BytesIO(file)
            else:
                # Ensure PdfReader gets bytes or seekable BytesIO (e.g. avoid raw SpooledTemporaryFile)
                if hasattr(file, "read") and not isinstance(file, io.BytesIO):
                    file = io.BytesIO(file.read())
            reader = PdfReader(file)
        else:
            return result

        if not reader.outline:
            return result

        outline = reader.outline
        if not isinstance(outline, list):
            outline = [outline]

        def _extract_outline_recursive(
            outline_items: list, level: int, out: List[dict[str, Any]]
        ) -> None:
            """Recursively extract outline items. pypdf uses nested lists for children."""
            for item in outline_items:
                if isinstance(item, list):
                    _extract_outline_recursive(item, level + 1, out)
                else:
                    page_num = None
                    if hasattr(item, "page") and item.page is not None:
                        if isinstance(item.page, int):
                            # pypdf may return 0-based index; convert to 1-based for partitioner
                            page_num = (item.page + 1) if OUTLINE_PAGE_ONE_BASED else item.page
                        elif hasattr(item.page, "get_object"):
                            page_obj = item.page.get_object()
                            if isinstance(page_obj, dict) and "/Type" in page_obj:
                                for i, page in enumerate(reader.pages):
                                    if page.get_object() == page_obj:
                                        page_num = (i + 1) if OUTLINE_PAGE_ONE_BASED else i
                                        break
                    title = item.title if hasattr(item, "title") else str(item)
                    out.append({"title": title, "level": level, "page": page_num})

        _extract_outline_recursive(outline, level=0, out=result)

    except (MemoryError, RecursionError):
        raise
    except Exception as e:
        logger.debug(f"Failed to extract PDF outline: {e}")

    return result


def infer_heading_levels_from_outline(
    elements: list[Element],
    outline_entries: list[dict[str, Any]],
    fuzzy_match_threshold: float = 0.85,
) -> None:
    """Assign heading levels to Title elements based on PDF outline.

    Outline page numbers are 1-based to match element.metadata.page_number.

    Args:
        elements: List of elements to update
        outline_entries: List of outline entries from PDF (page 1-based)
        fuzzy_match_threshold: Threshold for fuzzy text matching (0.0-1.0); default 0.85 reduces false positives (e.g. "Part I" vs "Part II")
    """
    from difflib import SequenceMatcher

    # Bucket outline entries by page number (1-based), keeping first occurrence per (page, title).
    outline_by_page: Dict[Optional[int], Dict[str, int]] = {}
    for entry in outline_entries:
        title = entry.get("title", "").strip()
        level = entry.get("level", 0)
        page = entry.get("page")
        normalized_level = _clamp_heading_level(level + 1)
        key = title.lower()
        page_bucket = outline_by_page.setdefault(page, {})
        if key not in page_bucket:
            page_bucket[key] = normalized_level

    global_outline_map: Dict[str, int] = {}
    for page_bucket in outline_by_page.values():
        for k, v in page_bucket.items():
            if k not in global_outline_map:
                global_outline_map[k] = v

    def get_candidates(page: Optional[int]) -> Dict[str, int]:
        return outline_by_page.get(page, {})

    candidate_order = [
        get_candidates(None),
        global_outline_map,
    ]

    for element in elements:
        if not isinstance(element, Title) or not element.metadata:
            continue
        element_text = element.text.strip().lower()
        page_number = element.metadata.page_number
        # Same-page first, then page-agnostic, then global
        candidate_maps = [get_candidates(page_number)] + candidate_order

        best_match_level = None
        best_match_score = 0.0

        for candidate_map in candidate_maps:
            if element_text in candidate_map:
                best_match_level = candidate_map[element_text]
                best_match_score = 1.0
                break

        if best_match_level is None:
            for candidate_map in candidate_maps:
                for outline_title, lvl in candidate_map.items():
                    similarity = SequenceMatcher(None, element_text, outline_title).ratio()
                    if similarity > best_match_score and similarity >= fuzzy_match_threshold:
                        best_match_score = similarity
                        best_match_level = lvl
                        if similarity >= 1.0:
                            break
                if best_match_level is not None and best_match_score >= fuzzy_match_threshold:
                    break

        if best_match_level is not None:
            element.metadata.heading_level = _clamp_heading_level(best_match_level)


def infer_heading_levels_by_document_order(
    elements: list[Element],
) -> None:
    """Assign heading levels to Title elements by document-wide order.

    When PDF outline is unavailable or did not assign a level, assigns levels by
    document order (page, then position): first title in doc = H1, second = H2, etc.
    Only assigns to titles that do not already have heading_level set (e.g. by outline).
    Levels are 1-based and clamped to 1-6.

    Args:
        elements: Full list of elements (Title elements without level will be assigned)
    """
    title_elements = [e for e in elements if isinstance(e, Title) and e.metadata is not None]
    if not title_elements:
        return

    index_by_id = {id(e): i for i, e in enumerate(elements)}

    def doc_order_key(el: Element) -> tuple[int, int]:
        page = el.metadata.page_number or 1
        idx = index_by_id.get(id(el), 0)
        return (page, idx)

    sorted_titles = sorted(title_elements, key=doc_order_key)
    num_titles = len(sorted_titles)

    for idx, element in enumerate(sorted_titles):
        if element.metadata.heading_level is not None:
            continue
        if num_titles <= 6:
            level = idx + 1
        else:
            percentile = (idx + 1) / num_titles
            level = int(percentile * 6) + 1
        element.metadata.heading_level = _clamp_heading_level(level)


def infer_heading_levels(
    elements: list[Element],
    filename: Optional[str] = None,
    file: Optional[io.BytesIO | bytes] = None,
    use_outline: bool = True,
    use_font_analysis: bool = True,
) -> list[Element]:
    """Infer hierarchical heading levels (H1-H6) for Title elements in PDF.

    This function combines multiple strategies to determine heading levels:
    1. PDF outline/bookmarks (most reliable)
    2. Font size analysis (fallback)

    Args:
        elements: List of extracted elements
        filename: Path to PDF file (for outline extraction)
        file: File-like object or bytes containing PDF content
        use_outline: Whether to use PDF outline for hierarchy detection
        use_font_analysis: Whether to use font size analysis as fallback

    Returns:
        List of elements with heading_level metadata assigned to Title elements
    """
    # First, try to use PDF outline
    if use_outline:
        try:
            outline_entries = extract_pdf_outline(filename=filename, file=file)
            if outline_entries:
                infer_heading_levels_from_outline(elements, outline_entries)
        except (MemoryError, RecursionError):
            raise
        except Exception as e:
            logger.debug(f"Failed during outline-based heading inference: {e}")

    # For elements without heading_level, use document-order fallback (relative to all titles)
    if use_font_analysis:
        if any(
            isinstance(e, Title) and (e.metadata is None or e.metadata.heading_level is None)
            for e in elements
        ):
            infer_heading_levels_by_document_order(elements)

    return elements
