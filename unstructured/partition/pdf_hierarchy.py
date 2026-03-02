"""Utilities for detecting hierarchical heading levels in PDF documents.

This module infers heading levels (H1–H6) for PDF documents by analyzing:
1. PDF document outline/bookmarks
2. Font sizes relative to page size and other headings
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional

from pypdf import PdfReader

from unstructured.documents.elements import Element, Title
from unstructured.logger import logger


def extract_pdf_outline(
    filename: Optional[str] = None, file: Optional[io.BytesIO | bytes] = None
) -> list[dict[str, Any]]:
    """Extract PDF outline/bookmarks structure.

    Args:
        filename: Path to PDF file
        file: File-like object or bytes containing PDF content

    Returns:
        List of outline entries with 'title', 'level', and 'page' information
    """
    outline_entries = []

    try:
        if filename:
            reader = PdfReader(filename)
        elif file:
            if isinstance(file, bytes):
                file = io.BytesIO(file)
            reader = PdfReader(file)
        else:
            return outline_entries

        if reader.outline:

            def _extract_outline_recursive(outline_items, level: int):
                """Recursively extract outline items.

                pypdf outline: list of Destination items and/or nested lists.
                - Destination: outline item at current level
                - List: children of the preceding item; recurse with level+1
                """
                for item in outline_items:
                    if isinstance(item, list):
                        _extract_outline_recursive(item, level + 1)
                    else:
                        page_num = None
                        if hasattr(item, "page") and item.page is not None:
                            if isinstance(item.page, int):
                                page_num = item.page
                            elif hasattr(item.page, "get_object"):
                                page_obj = item.page.get_object()
                                if isinstance(page_obj, dict) and "/Type" in page_obj:
                                    for i, page in enumerate(reader.pages):
                                        if page.get_object() == page_obj:
                                            page_num = i
                                            break

                        title = item.title if hasattr(item, "title") else str(item)
                        outline_entries.append({"title": title, "level": level, "page": page_num})

                        if hasattr(item, "children") and item.children:
                            _extract_outline_recursive(
                                item.children
                                if isinstance(item.children, list)
                                else [item.children],
                                level + 1,
                            )

            outline = reader.outline
            if not isinstance(outline, list):
                outline = [outline]
            _extract_outline_recursive(outline, level=0)

    except Exception as e:
        logger.warning(f"Failed to extract PDF outline: {e}")

    return outline_entries


def infer_heading_levels_from_outline(
    elements: list[Element],
    outline_entries: list[dict[str, Any]],
    fuzzy_match_threshold: float = 0.8,
) -> None:
    """Assign heading levels to Title elements based on PDF outline.

    Args:
        elements: List of elements to update
        outline_entries: List of outline entries from PDF
        fuzzy_match_threshold: Threshold for fuzzy text matching (0.0-1.0)
    """
    from difflib import SequenceMatcher

    # Bucket outline entries by page number, keeping first occurrence per (page, title).
    outline_by_page: Dict[Optional[int], Dict[str, int]] = {}
    for entry in outline_entries:
        title = entry.get("title", "").strip()
        level = entry.get("level", 0)
        page = entry.get("page")
        # Normalize level to 1-6 range (H1-H6)
        normalized_level = min(max(level + 1, 1), 6)
        key = title.lower()
        page_bucket = outline_by_page.setdefault(page, {})
        if key not in page_bucket:
            page_bucket[key] = normalized_level

    # Precompute a global fallback map in case page-number matching fails.
    global_outline_map: Dict[str, int] = {}
    for page_bucket in outline_by_page.values():
        for k, v in page_bucket.items():
            if k not in global_outline_map:
                global_outline_map[k] = v

    # Match Title elements to outline entries, preferring same-page matches when possible.
    for element in elements:
        if isinstance(element, Title) and element.metadata:
            element_text = element.text.strip().lower()
            page_number = element.metadata.page_number

            best_match_level = None
            best_match_score = 0.0

            def candidates_for_page(page: Optional[int]) -> Dict[str, int]:
                return outline_by_page.get(page, {})

            # 1) Exact match on same page, then on any page.
            for candidate_map in (
                candidates_for_page(page_number),
                candidates_for_page(None),
                global_outline_map,
            ):
                if element_text in candidate_map:
                    best_match_level = candidate_map[element_text]
                    best_match_score = 1.0
                    break

            # 2) Fuzzy match if no exact match found.
            if best_match_level is None:
                for candidate_map in (
                    candidates_for_page(page_number),
                    candidates_for_page(None),
                    global_outline_map,
                ):
                    for outline_title, level in candidate_map.items():
                        similarity = SequenceMatcher(None, element_text, outline_title).ratio()
                        if similarity > best_match_score and similarity >= fuzzy_match_threshold:
                            best_match_score = similarity
                            best_match_level = level
                            # Perfect match; no need to keep searching this map.
                            if similarity >= 1.0:
                                break
                    if best_match_level is not None and best_match_score >= fuzzy_match_threshold:
                        break

            if best_match_level is not None:
                element.metadata.heading_level = best_match_level


def infer_heading_levels_from_font_sizes(
    elements: list[Element],
) -> None:
    """Assign heading levels to Title elements using document-wide ordering.

    When PDF outline is unavailable, assigns levels by document order (page, then
    position): first title in doc = H1, subsequent titles get H2-H6 by percentile.
    Single title in whole doc gets H1.
    Note: layout_elements_map is accepted for API compatibility but is not used.

    Args:
        elements: List of elements to update
    """
    title_elements = [e for e in elements if isinstance(e, Title) and e.metadata is not None]

    if not title_elements:
        return

    if len(title_elements) == 1:
        if title_elements[0].metadata.heading_level is None:
            title_elements[0].metadata.heading_level = 1
        return

    # Document-wide: sort by (page_number, element order in input list)
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
            level = min(6, max(1, int(percentile * 6) + 1))
        element.metadata.heading_level = level


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
        except Exception as e:
            logger.warning(f"Failed during outline-based heading inference: {e}")

    # For elements without heading_level, use font size analysis
    if use_font_analysis:
        elements_without_level = [
            e
            for e in elements
            if isinstance(e, Title) and (e.metadata is None or e.metadata.heading_level is None)
        ]
        if elements_without_level:
            infer_heading_levels_from_font_sizes(elements_without_level)

    return elements
