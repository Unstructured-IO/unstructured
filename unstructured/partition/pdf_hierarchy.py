"""Utilities for detecting hierarchical heading levels in PDF documents.

This module provides functionality to infer heading levels (H1, H2, H3, H4, H5, H6) for PDF documents
by analyzing:
1. PDF document outline/bookmarks
2. Font sizes relative to page size and other headings
"""

from __future__ import annotations

import io
from collections import defaultdict
from typing import Optional

from pypdf import PdfReader
from unstructured.documents.elements import Element, Title


def extract_pdf_outline(
    filename: Optional[str] = None, file: Optional[io.BytesIO | bytes] = None
) -> list[dict[str, any]]:
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
            def _extract_outline_recursive(outline_item, level: int = 0):
                """Recursively extract outline items."""
                if isinstance(outline_item, list):
                    for item in outline_item:
                        _extract_outline_recursive(item, level)
                else:
                    # Get page number
                    page_num = None
                    if hasattr(outline_item, 'page') and outline_item.page is not None:
                        if isinstance(outline_item.page, int):
                            page_num = outline_item.page
                        elif hasattr(outline_item.page, 'get_object'):
                            page_obj = outline_item.page.get_object()
                            if isinstance(page_obj, dict) and '/Type' in page_obj:
                                # Find page number
                                for i, page in enumerate(reader.pages):
                                    if page.get_object() == page_obj:
                                        page_num = i
                                        break

                    title = outline_item.title if hasattr(outline_item, 'title') else str(outline_item)
                    outline_entries.append({
                        'title': title,
                        'level': level,
                        'page': page_num
                    })

                    # Process children
                    if hasattr(outline_item, 'children') and outline_item.children:
                        _extract_outline_recursive(outline_item.children, level + 1)

            _extract_outline_recursive(reader.outline, level=0)

    except Exception as e:
        # If outline extraction fails, return empty list
        # This is not a critical error - we can still use font size analysis
        pass

    return outline_entries


def extract_font_info_from_layout_element(
    layout_element: any,
) -> dict[str, any]:
    """Extract font information from a PDFMiner layout element.

    Args:
        layout_element: PDFMiner layout element (LTTextBox, LTTextLine, etc.)

    Returns:
        Dictionary with font size, font name, and other font properties
    """
    font_info = {
        "font_size": None,
        "font_name": None,
        "is_bold": False,
        "is_italic": False,
    }

    try:
        if hasattr(layout_element, "chars"):
            # Extract font info from characters
            font_sizes = []
            font_names = set()
            for char in layout_element.chars:
                if hasattr(char, "fontname"):
                    font_names.add(char.fontname)
                if hasattr(char, "size"):
                    font_sizes.append(char.size)
                if hasattr(char, "fontname"):
                    font_name_lower = char.fontname.lower()
                    if "bold" in font_name_lower:
                        font_info["is_bold"] = True
                    if "italic" in font_name_lower or "oblique" in font_name_lower:
                        font_info["is_italic"] = True

            if font_sizes:
                font_info["font_size"] = sum(font_sizes) / len(font_sizes)
            if font_names:
                font_info["font_name"] = list(font_names)[0] if len(font_names) == 1 else list(font_names)

        elif hasattr(layout_element, "get_text"):
            # Try to get font info from text container
            if hasattr(layout_element, "fontname"):
                font_info["font_name"] = layout_element.fontname
            if hasattr(layout_element, "size"):
                font_info["font_size"] = layout_element.size

    except Exception:
        # If extraction fails, return default info
        pass

    return font_info


def analyze_font_sizes_from_pdfminer(
    elements: list[Element],
    layout_elements_map: Optional[dict[str, any]] = None,
    page_width: float = 612.0,  # Default US Letter width in points
    page_height: float = 792.0,  # Default US Letter height in points
) -> dict[str, float]:
    """Analyze font sizes from PDF elements to determine heading hierarchy.

    Args:
        elements: List of extracted elements
        layout_elements_map: Optional mapping of element text to PDFMiner layout elements
        page_width: Width of the page in points
        page_height: Height of the page in points

    Returns:
        Dictionary mapping element text to average font size
    """
    font_sizes = {}
    
    if layout_elements_map:
        for text, layout_element in layout_elements_map.items():
            font_info = extract_font_info_from_layout_element(layout_element)
            if font_info["font_size"] is not None:
                font_sizes[text] = font_info["font_size"]
    
    return font_sizes


def infer_heading_levels_from_outline(
    elements: list[Element],
    outline_entries: list[dict[str, any]],
    fuzzy_match_threshold: float = 0.8,
) -> None:
    """Assign heading levels to Title elements based on PDF outline.

    Args:
        elements: List of elements to update
        outline_entries: List of outline entries from PDF
        fuzzy_match_threshold: Threshold for fuzzy text matching (0.0-1.0)
    """
    from difflib import SequenceMatcher

    # Create a mapping of outline titles to levels
        outline_map = {}
        for entry in outline_entries:
            title = entry.get('title', '').strip()
            level = entry.get('level', 0)
            # Normalize level to 1-6 range (H1-H6)
            normalized_level = min(max(level + 1, 1), 6)
            outline_map[title.lower()] = normalized_level

    # Match Title elements to outline entries
    for element in elements:
        if isinstance(element, Title) and element.metadata:
            element_text = element.text.strip().lower()
            best_match_level = None
            best_match_score = 0.0

            # Try exact match first
            if element_text in outline_map:
                best_match_level = outline_map[element_text]
                best_match_score = 1.0
            else:
                # Try fuzzy matching
                for outline_title, level in outline_map.items():
                    similarity = SequenceMatcher(None, element_text, outline_title).ratio()
                    if similarity > best_match_score and similarity >= fuzzy_match_threshold:
                        best_match_score = similarity
                        best_match_level = level

            if best_match_level is not None:
                # Ensure level is in valid range (1-6)
                element.metadata.heading_level = min(max(best_match_level, 1), 6)


def infer_heading_levels_from_font_sizes(
    elements: list[Element],
    layout_elements_map: Optional[dict[str, any]] = None,
    page_width: float = 612.0,
    page_height: float = 792.0,
) -> None:
    """Assign heading levels to Title elements based on relative font sizes.

    This function analyzes font sizes of Title elements and assigns heading levels
    based on size relative to the page and other headings.

    Args:
        elements: List of elements to update
        layout_elements_map: Optional mapping of element text to PDFMiner layout elements
        page_width: Width of the page in points
        page_height: Height of the page in points
    """
    # Extract Title elements with their characteristics
    title_elements = []
    for element in elements:
        if isinstance(element, Title) and element.metadata:
            title_elements.append(element)

    if len(title_elements) < 2:
        # Not enough titles to determine hierarchy
        return

    # Try to extract actual font sizes if layout elements are available
    font_sizes_map = {}
    if layout_elements_map:
        font_sizes_map = analyze_font_sizes_from_pdfminer(
            title_elements,
            layout_elements_map=layout_elements_map,
            page_width=page_width,
            page_height=page_height,
        )

    # Group titles by page to analyze relative sizes
    titles_by_page: dict[int, list[Element]] = defaultdict(list)
    for element in title_elements:
        page_num = element.metadata.page_number or 1
        titles_by_page[page_num].append(element)

    # For each page, analyze relative sizes
    for page_num, page_titles in titles_by_page.items():
        if len(page_titles) < 2:
            continue

        title_scores = []
        for element in page_titles:
            text = element.text.strip()
            
            # If we have actual font size, use it
            if text in font_sizes_map:
                # Higher font size = higher level (H1)
                score = font_sizes_map[text]
            else:
                # Fallback to heuristic based on text characteristics
                word_count = len(text.split())
                char_count = len(text)
                is_mostly_uppercase = (
                    text.isupper() or
                    (len(text) > 0 and text[0].isupper() and
                     sum(1 for c in text if c.isupper()) / max(len(text), 1) > 0.5)
                )
                
                # Score: higher for shorter, more capitalized titles
                # Normalize to a reasonable range (10-30 points)
                base_score = 20.0
                word_penalty = word_count * 0.5
                capitalization_bonus = 5.0 if is_mostly_uppercase else 0.0
                score = base_score - word_penalty + capitalization_bonus
            
            title_scores.append((element, score))

        # Sort by score (descending) to get hierarchy
        title_scores.sort(key=lambda x: x[1], reverse=True)

        # Assign levels based on ranking
        # Distribute across H1-H6 based on percentile
        num_titles = len(title_scores)
        for idx, (element, _) in enumerate(title_scores):
            if num_titles <= 6:
                level = idx + 1
            else:
                percentile = (idx + 1) / num_titles
                if percentile <= 1/6:
                    level = 1
                elif percentile <= 2/6:
                    level = 2
                elif percentile <= 3/6:
                    level = 3
                elif percentile <= 4/6:
                    level = 4
                elif percentile <= 5/6:
                    level = 5
                else:
                    level = 6
            
            # Only assign if not already set
            if element.metadata.heading_level is None:
                element.metadata.heading_level = min(max(level, 1), 6)


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
        except Exception:
            # If outline extraction fails, continue with font analysis
            pass

    # For elements without heading_level, use font size analysis
    if use_font_analysis:
        elements_without_level = [
            e for e in elements
            if isinstance(e, Title) and (e.metadata is None or e.metadata.heading_level is None)
        ]
        if elements_without_level:
            infer_heading_levels_from_font_sizes(elements_without_level)

    return elements

