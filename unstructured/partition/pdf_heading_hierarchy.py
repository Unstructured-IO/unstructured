"""Infer hierarchical heading levels (H1-H6) for PDF elements.

Two strategies in order of preference:
1. Outline extraction - match PDF bookmarks to Title elements by page + text similarity.
2. Font-size analysis - cluster distinct font sizes across Titles, largest font -> depth 0.

Sets element.metadata.category_depth using the 0-indexed convention (0=H1, 1=H2, ... 5=H6).
"""

from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import IO, Optional

from pypdf import PdfReader

from unstructured.documents.elements import Element, Title
from unstructured.logger import logger

_SIMILARITY_THRESHOLD = 0.85
_MAX_HEADING_DEPTH = 6


def infer_heading_levels(
    elements: list[Element],
    *,
    filename: str = "",
    file: Optional[IO[bytes]] = None,
    password: Optional[str] = None,
) -> list[Element]:
    """Assign ``category_depth`` to ``Title`` elements based on PDF structure.
    Mutates *elements* in-place and returns for convenience.
    """
    titles = [el for el in elements if isinstance(el, Title)]
    if not titles:
        return elements
    reader = _open_reader(filename=filename, file=file, password=password)
    if reader is None:
        return elements
    _apply_outline_levels(titles, reader)
    if any(t.metadata.category_depth is None for t in titles):
        _apply_font_size_levels(titles, filename=filename, file=file, password=password)
    return elements


# -- Strategy 1: PDF outline / bookmarks --


def _apply_outline_levels(titles: list[Title], reader: PdfReader) -> int:
    """Walk the PDF outline tree and set ``category_depth`` on matching titles.
    Returns the number of matched titles.
    """
    try:
        outline = reader.outline
    except Exception:
        logger.debug("Failed to read PDF outline, skipping outline strategy.")
        return 0
    if not outline:
        return 0

    outline_entries: list[tuple[str, int, Optional[int]]] = []
    _walk_outline(outline, reader, depth=0, entries=outline_entries)
    if not outline_entries:
        return 0

    titles_by_page: dict[Optional[int], list[Title]] = defaultdict(list)
    for title in titles:
        titles_by_page[title.metadata.page_number].append(title)

    matched = 0
    for entry_text, depth, page_number in outline_entries:
        capped_depth = min(depth, _MAX_HEADING_DEPTH - 1)
        candidates = titles_by_page.get(page_number, [])
        best_title, best_ratio = _best_match(entry_text, candidates)
        if best_ratio < _SIMILARITY_THRESHOLD:
            all_unmatched = [t for t in titles if t.metadata.category_depth is None]
            best_title, best_ratio = _best_match(entry_text, all_unmatched)
        if best_title is not None and best_ratio >= _SIMILARITY_THRESHOLD:
            best_title.metadata.category_depth = capped_depth
            matched += 1
    return matched


def _walk_outline(
    items: list,
    reader: PdfReader,
    depth: int,
    entries: list[tuple[str, int, Optional[int]]],
) -> None:
    """Recursively walk an outline tree produced by ``PdfReader.outline``."""
    for item in items:
        if isinstance(item, list):
            _walk_outline(item, reader, depth + 1, entries)
        else:
            title_text = (getattr(item, "title", None) or "").strip()
            if not title_text:
                continue
            entries.append((title_text, depth, _resolve_page_number(item, reader)))


def _resolve_page_number(destination, reader: PdfReader) -> Optional[int]:
    """Return the 1-based page number for an outline destination."""
    try:
        page_obj = destination.page
        if page_obj is None:
            return None
        page_obj = page_obj.get_object() if hasattr(page_obj, "get_object") else page_obj
        for idx, page in enumerate(reader.pages):
            if page.get_object() == page_obj:
                return idx + 1
    except Exception:
        pass
    return None


def _best_match(query: str, candidates: list[Title]) -> tuple[Optional[Title], float]:
    """Find the unassigned candidate Title most similar to *query*.
    Always evaluates all candidates (never breaks early on a weaker match).
    """
    best_title: Optional[Title] = None
    best_ratio = 0.0
    query_lower = query.lower().strip()
    for title in candidates:
        if title.metadata.category_depth is not None:
            continue
        title_text = (title.text or "").strip().lower()
        if not title_text:
            continue
        ratio = SequenceMatcher(None, query_lower, title_text).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_title = title
    return best_title, best_ratio


# -- Strategy 2: Font-size clustering --


def _apply_font_size_levels(
    titles: list[Title],
    *,
    filename: str = "",
    file: Optional[IO[bytes]] = None,
    password: Optional[str] = None,
) -> None:
    """Assign ``category_depth`` based on font-size clusters.
    Ranks distinct sizes largest-first -> depth 0, 1, ...
    """
    try:
        page_font_data = _extract_page_font_data(filename=filename, file=file, password=password)
    except Exception:
        logger.debug("Font-size analysis failed, skipping fallback.", exc_info=True)
        return
    if not page_font_data:
        return

    # Map ALL titles to font sizes (for full size->depth mapping).
    all_title_sizes: dict[int, float] = {}
    for idx, title in enumerate(titles):
        page_num = title.metadata.page_number
        if page_num is None or page_num not in page_font_data:
            continue
        title_text = (title.text or "").strip()
        if not title_text:
            continue
        best_size: Optional[float] = None
        best_ratio = 0.0
        for box_text, dominant_size in page_font_data[page_num]:
            ratio = SequenceMatcher(None, title_text.lower(), box_text.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_size = dominant_size
        if best_size is not None and best_ratio >= 0.5:
            all_title_sizes[idx] = best_size
    if not all_title_sizes:
        return

    distinct_sizes = sorted(set(all_title_sizes.values()), reverse=True)
    size_to_depth = {size: min(i, _MAX_HEADING_DEPTH - 1) for i, size in enumerate(distinct_sizes)}
    for idx, size in all_title_sizes.items():
        if titles[idx].metadata.category_depth is None:
            titles[idx].metadata.category_depth = size_to_depth[size]


def _extract_page_font_data(
    *,
    filename: str = "",
    file: Optional[IO[bytes]] = None,
    password: Optional[str] = None,
) -> dict[int, list[tuple[str, float]]]:
    """Extract per-page (text, dominant_font_size) pairs using pdfminer."""
    page_font_data: dict[int, list[tuple[str, float]]] = {}
    if filename:
        with open(filename, "rb") as fp:
            _collect_font_data(fp, password, page_font_data)
    elif file:
        if hasattr(file, "seek"):
            file.seek(0)
        _collect_font_data(file, password, page_font_data)
    return page_font_data


def _collect_font_data(
    fp: IO[bytes],
    password: Optional[str],
    page_font_data: dict[int, list[tuple[str, float]]],
) -> None:
    """Iterate pdfminer pages and collect (text, dominant_font_size) pairs."""
    from pdfminer.layout import LTChar, LTTextBox, LTTextLine

    from unstructured.partition.pdf_image.pdfminer_utils import open_pdfminer_pages_generator

    for page_number, (_page, page_layout) in enumerate(
        open_pdfminer_pages_generator(fp, password=password),
        start=1,
    ):
        page_entries: list[tuple[str, float]] = []
        for element in page_layout:
            if not isinstance(element, LTTextBox):
                continue
            text = element.get_text().strip()
            if not text:
                continue
            char_sizes: list[float] = []
            for line in element:
                if isinstance(line, LTTextLine):
                    for char in line:
                        if isinstance(char, LTChar) and char.size > 0:
                            char_sizes.append(char.size)
            if char_sizes:
                page_entries.append((text, _mode_font_size(char_sizes)))
        page_font_data[page_number] = page_entries


def _mode_font_size(sizes: list[float]) -> float:
    """Return the most common font size (rounded to 1 decimal)."""
    counts: dict[float, int] = {}
    for s in sizes:
        r = round(s, 1)
        counts[r] = counts.get(r, 0) + 1
    return max(counts, key=counts.get)  # type: ignore[arg-type]


# -- Helpers --


def _open_reader(
    *,
    filename: str = "",
    file: Optional[IO[bytes]] = None,
    password: Optional[str] = None,
) -> Optional[PdfReader]:
    """Open a PdfReader, returning None on failure."""
    try:
        kwargs = {"password": password} if password else {}
        if filename:
            return PdfReader(filename, **kwargs)
        elif file:
            if hasattr(file, "seek"):
                file.seek(0)
            return PdfReader(file, **kwargs)
        return None
    except Exception:
        logger.debug("Could not open PdfReader for heading inference.", exc_info=True)
        return None
