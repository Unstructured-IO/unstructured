"""Infer hierarchical heading levels (H1-H6) for PDF elements.

Two strategies in order of preference:
1. Outline extraction - match PDF bookmarks to Title elements by destination + text similarity.
2. Font-size analysis - cluster distinct font sizes across Titles, largest font -> depth 0.

Sets element.metadata.category_depth using the 0-indexed convention (0=H1, 1=H2, ... 5=H6).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import IO, Any, BinaryIO, Optional, cast

from pypdf import PdfReader

from unstructured.documents.coordinates import CoordinateSystem, PointSpace
from unstructured.documents.elements import Element, Title
from unstructured.logger import logger

_SIMILARITY_THRESHOLD = 0.85
_MAX_HEADING_DEPTH = 6


@dataclass(frozen=True)
class _OutlineEntry:
    text: str
    depth: int
    page_number: int
    left: Optional[float] = None
    top: Optional[float] = None
    right: Optional[float] = None
    bottom: Optional[float] = None

    @property
    def has_destination_coordinates(self) -> bool:
        return any(
            coordinate is not None for coordinate in (self.left, self.top, self.right, self.bottom)
        )


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

    outline_entries: list[_OutlineEntry] = []
    _walk_outline(outline, reader, depth=0, entries=outline_entries)
    if not outline_entries:
        return 0

    titles_by_page: dict[int, list[Title]] = defaultdict(list)
    for title in titles:
        if title.metadata.page_number is not None:
            titles_by_page[title.metadata.page_number].append(title)

    matched = 0
    for entry in outline_entries:
        capped_depth = min(entry.depth, _MAX_HEADING_DEPTH - 1)
        candidates = titles_by_page.get(entry.page_number, [])
        best_title, best_ratio = _best_destination_match(entry, candidates, reader)
        if best_title is None:
            best_title, best_ratio = _best_match(entry.text, candidates)
        if best_title is not None and best_ratio >= _SIMILARITY_THRESHOLD:
            best_title.metadata.category_depth = capped_depth
            matched += 1
    return matched


def _walk_outline(
    items: list[Any],
    reader: PdfReader,
    depth: int,
    entries: list[_OutlineEntry],
) -> None:
    """Recursively walk an outline tree produced by ``PdfReader.outline``."""
    for item in items:
        if isinstance(item, list):
            _walk_outline(item, reader, depth + 1, entries)
        else:
            title_text = (getattr(item, "title", None) or "").strip()
            if not title_text:
                continue
            page_number = _resolve_page_number(item, reader)
            if page_number is None:
                continue
            entries.append(
                _OutlineEntry(
                    text=title_text,
                    depth=depth,
                    page_number=page_number,
                    left=_as_float(getattr(item, "left", None)),
                    top=_as_float(getattr(item, "top", None)),
                    right=_as_float(getattr(item, "right", None)),
                    bottom=_as_float(getattr(item, "bottom", None)),
                ),
            )


def _resolve_page_number(destination: object, reader: PdfReader) -> Optional[int]:
    """Return the 1-based page number for an outline destination."""
    try:
        page_idx = reader.get_destination_page_number(cast(Any, destination))
        if page_idx is not None and page_idx >= 0:
            return page_idx + 1
    except Exception:
        pass

    try:
        page_obj = getattr(destination, "page", None)
        if page_obj is None:
            return None
        if isinstance(page_obj, int):
            return page_obj + 1 if page_obj >= 0 else None
        page_obj = page_obj.get_object() if hasattr(page_obj, "get_object") else page_obj
        for idx, page in enumerate(reader.pages):
            if page.get_object() == page_obj:
                return idx + 1
    except Exception:
        pass
    return None


def _as_float(value: Any) -> Optional[float]:
    """Return *value* as a float when it is a numeric PDF destination coordinate."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_destination_match(
    entry: _OutlineEntry,
    candidates: list[Title],
    reader: PdfReader,
) -> tuple[Optional[Title], float]:
    """Find the unassigned candidate nearest the outline destination on the target page."""
    if not entry.has_destination_coordinates:
        return None, 0.0

    best_title: Optional[Title] = None
    best_ratio = 0.0
    best_distance = float("inf")
    query_lower = entry.text.lower().strip()
    for title in candidates:
        if title.metadata.category_depth is not None:
            continue
        title_text = (title.text or "").strip().lower()
        if not title_text:
            continue
        ratio = SequenceMatcher(None, query_lower, title_text).ratio()
        if ratio < _SIMILARITY_THRESHOLD:
            continue
        distance = _distance_to_destination(entry, title, reader)
        if distance is None:
            continue
        if distance < best_distance or (distance == best_distance and ratio > best_ratio):
            best_distance = distance
            best_ratio = ratio
            best_title = title
    return best_title, best_ratio


def _distance_to_destination(
    entry: _OutlineEntry,
    title: Title,
    reader: PdfReader,
) -> Optional[float]:
    """Return distance from the outline destination point to a Title bounding box."""
    coordinates = title.metadata.coordinates
    if coordinates is None or coordinates.points is None or coordinates.system is None:
        return None

    destination_point = _destination_point_in_coordinate_system(entry, coordinates.system, reader)
    if destination_point is None:
        return None
    destination_x, destination_y = destination_point
    if destination_x is None and destination_y is None:
        return None

    xs = [point[0] for point in coordinates.points]
    ys = [point[1] for point in coordinates.points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    dx = _axis_distance(destination_x, x_min, x_max)
    dy = _axis_distance(destination_y, y_min, y_max)
    return (dx**2 + dy**2) ** 0.5


def _destination_point_in_coordinate_system(
    entry: _OutlineEntry,
    coordinate_system: CoordinateSystem,
    reader: PdfReader,
) -> Optional[tuple[Optional[float], Optional[float]]]:
    """Convert the PDF outline destination point into an element coordinate system."""
    pdf_x = entry.left if entry.left is not None else entry.right
    pdf_y = entry.top if entry.top is not None else entry.bottom
    if pdf_x is None and pdf_y is None:
        return None

    page_space = _page_point_space(reader, entry.page_number)
    if page_space is None:
        return None

    converted_x, converted_y = page_space.convert_coordinates_to_new_system(
        new_system=coordinate_system,
        x=pdf_x if pdf_x is not None else 0,
        y=pdf_y if pdf_y is not None else 0,
    )
    return (
        converted_x if pdf_x is not None else None,
        converted_y if pdf_y is not None else None,
    )


def _page_point_space(reader: PdfReader, page_number: int) -> Optional[PointSpace]:
    """Return the PDF point-space for *page_number*."""
    try:
        page = reader.pages[page_number - 1]
        box = getattr(page, "cropbox", None) or page.mediabox
        return PointSpace(width=float(box.width), height=float(box.height))
    except Exception:
        return None


def _axis_distance(point: Optional[float], lower: float, upper: float) -> float:
    """Return zero when *point* falls inside the axis range, else edge distance."""
    if point is None:
        return 0.0
    if point < lower:
        return lower - point
    if point > upper:
        return point - upper
    return 0.0


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
        open_pdfminer_pages_generator(cast(BinaryIO, fp), password=password),
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
        if filename:
            return PdfReader(filename, password=password) if password else PdfReader(filename)
        elif file:
            if hasattr(file, "seek"):
                file.seek(0)
            return PdfReader(file, password=password) if password else PdfReader(file)
        return None
    except Exception:
        logger.debug("Could not open PdfReader for heading inference.", exc_info=True)
        return None
