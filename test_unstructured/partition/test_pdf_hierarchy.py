"""Test suite for PDF hierarchical heading detection."""

from __future__ import annotations

import pytest

from unstructured.documents.elements import (
    ElementMetadata,
    NarrativeText,
    Table,
    Title,
)
from unstructured.partition.pdf_hierarchy import (
    extract_pdf_outline,
    infer_heading_levels,
    infer_heading_levels_by_document_order,
    infer_heading_levels_from_outline,
)


class FakeOutlineItem:
    """Simple stand-in for pypdf outline items for testing outline extraction."""

    def __init__(self, title: str, page: int | None = None, children: list | None = None):
        self.title = title
        self.page = page
        self.children = children or []


def test_extract_pdf_outline_nested_lists(monkeypatch: pytest.MonkeyPatch):
    """Outline extraction should respect nested list hierarchy levels."""

    # pypdf uses nested lists for children: [ Root, [ Child, [ Grandchild ] ] ]
    root = FakeOutlineItem("Root", page=0)
    child = FakeOutlineItem("Child", page=1)
    grandchild = FakeOutlineItem("Grandchild", page=2)
    outline_structure = [root, [child, [grandchild]]]

    class FakeReader:
        def __init__(self, *_args, **_kwargs):
            self.outline = outline_structure
            # Only used for page index resolution; dummy objects are fine here.
            self.pages = [object(), object(), object()]

    # Patch PdfReader used inside extract_pdf_outline to our fake implementation.
    monkeypatch.setattr(
        "unstructured.partition.pdf_hierarchy.PdfReader",
        FakeReader,
    )

    outline_entries = extract_pdf_outline(filename="dummy.pdf")

    # Expect hierarchy: Root -> Child -> Grandchild as levels 0, 1, 2 respectively.
    titles_and_levels = [(e["title"], e["level"]) for e in outline_entries]
    assert titles_and_levels == [
        ("Root", 0),
        ("Child", 1),
        ("Grandchild", 2),
    ]


def test_infer_heading_levels_from_outline():
    """Test inferring heading levels from PDF outline."""
    elements = [
        Title("Introduction", metadata=ElementMetadata()),
        Title("Chapter 1", metadata=ElementMetadata()),
        Title("Section 1.1", metadata=ElementMetadata()),
    ]

    outline_entries = [
        {"title": "Introduction", "level": 0, "page": 1},
        {"title": "Chapter 1", "level": 1, "page": 2},
        {"title": "Section 1.1", "level": 2, "page": 3},
    ]

    infer_heading_levels_from_outline(elements, outline_entries)

    assert elements[0].metadata.heading_level == 1
    assert elements[1].metadata.heading_level == 2
    assert elements[2].metadata.heading_level == 3


def test_infer_heading_levels_by_document_order():
    """Test inferring heading levels from document-wide ordering."""
    elements = [
        Title("MAIN TITLE", metadata=ElementMetadata(page_number=1)),
        Title("Subtitle", metadata=ElementMetadata(page_number=1)),
        Title("Another subtitle", metadata=ElementMetadata(page_number=2)),
        Title("Minor heading", metadata=ElementMetadata(page_number=2)),
    ]

    infer_heading_levels_by_document_order(elements)

    levels = [e.metadata.heading_level for e in elements if e.metadata.heading_level is not None]
    assert len(levels) == 4
    assert levels == [1, 2, 3, 4]


def test_infer_heading_levels_integration():
    """Test the integrated heading level inference function."""
    elements = [
        Title("Introduction", metadata=ElementMetadata(page_number=1)),
        Title("Chapter 1", metadata=ElementMetadata(page_number=2)),
    ]

    result = infer_heading_levels(
        elements,
        filename=None,
        file=None,
        use_outline=False,
        use_font_analysis=True,
    )

    assert len(result) == len(elements)
    assert result[0].metadata.heading_level == 1
    assert result[1].metadata.heading_level == 2


def test_infer_heading_levels_integration_with_outline(monkeypatch: pytest.MonkeyPatch):
    """Test integration when outline is available (use_outline path)."""
    elements = [
        Title("Introduction", metadata=ElementMetadata(page_number=1)),
        Title("Chapter 1", metadata=ElementMetadata(page_number=2)),
    ]

    def mock_extract_outline(*, filename=None, file=None):
        return [
            {"title": "Introduction", "level": 0, "page": 1},
            {"title": "Chapter 1", "level": 1, "page": 2},
        ]

    monkeypatch.setattr(
        "unstructured.partition.pdf_hierarchy.extract_pdf_outline",
        mock_extract_outline,
    )

    result = infer_heading_levels(
        elements,
        filename="dummy.pdf",
        file=None,
        use_outline=True,
        use_font_analysis=True,
    )

    assert result[0].metadata.heading_level == 1
    assert result[1].metadata.heading_level == 2


def test_fuzzy_matching_in_outline():
    """Test that fuzzy matching works for outline entries."""
    elements = [
        Title("Introduction to the Project", metadata=ElementMetadata()),
    ]

    outline_entries = [
        {"title": "Introduction", "level": 0, "page": 1},
    ]

    infer_heading_levels_from_outline(elements, outline_entries, fuzzy_match_threshold=0.5)

    # Should match "Introduction to the Project" with "Introduction" (level 0 -> H1)
    assert elements[0].metadata is not None
    assert elements[0].metadata.heading_level is not None
    assert elements[0].metadata.heading_level == 1


# ---- Missing Test Coverage (PastelStorm review) ----


def test_page_number_matching_1based_same_title_different_pages():
    """Page-specific matching uses 1-based page numbers; same title on different pages gets correct level."""
    # Outline: "Summary" as H1 on page 1, H2 on page 2
    outline_entries = [
        {"title": "Summary", "level": 0, "page": 1},
        {"title": "Summary", "level": 1, "page": 2},
    ]
    elements = [
        Title("Summary", metadata=ElementMetadata(page_number=1)),
        Title("Summary", metadata=ElementMetadata(page_number=2)),
    ]
    infer_heading_levels_from_outline(elements, outline_entries)
    assert elements[0].metadata.heading_level == 1
    assert elements[1].metadata.heading_level == 2


def test_extract_pdf_outline_invalid_file_returns_empty():
    """Error path: invalid or missing file returns empty list, no exception."""
    result = extract_pdf_outline(filename="/nonexistent/path.pdf")
    assert result == []
    result = extract_pdf_outline(filename=None, file=None)
    assert result == []


def test_infer_heading_levels_when_outline_extraction_fails_returns_elements(monkeypatch):
    """Error path: when outline extraction fails, elements are still returned (fallback or unchanged)."""
    def raise_err(*, filename=None, file=None):
        raise ValueError("corrupt PDF")

    monkeypatch.setattr(
        "unstructured.partition.pdf_hierarchy.extract_pdf_outline",
        raise_err,
    )
    elements = [
        Title("Only Title", metadata=ElementMetadata(page_number=1)),
    ]
    result = infer_heading_levels(
        elements,
        filename="dummy.pdf",
        file=None,
        use_outline=True,
        use_font_analysis=True,
    )
    assert result is elements
    assert elements[0].metadata.heading_level == 1  # fallback by document order


def test_more_than_six_titles_percentile_path():
    """>6 titles: document-order fallback uses percentile formula; levels clamped to 1-6."""
    elements = [
        Title(f"Title {i}", metadata=ElementMetadata(page_number=1 + (i // 4)))
        for i in range(8)
    ]
    infer_heading_levels_by_document_order(elements)
    levels = [e.metadata.heading_level for e in elements]
    assert all(1 <= lev <= 6 for lev in levels)
    assert 6 in levels


def test_mixed_element_types_only_title_gets_heading_level():
    """Only Title elements receive heading_level; NarrativeText and Table are unchanged."""
    elements = [
        Title("Heading", metadata=ElementMetadata(page_number=1)),
        NarrativeText("Some paragraph.", metadata=ElementMetadata(page_number=1)),
        Table("cell\tcell", metadata=ElementMetadata(page_number=1)),
    ]
    infer_heading_levels_by_document_order(elements)
    assert elements[0].metadata.heading_level == 1
    assert getattr(elements[1].metadata, "heading_level", None) is None
    assert getattr(elements[2].metadata, "heading_level", None) is None


def test_pre_existing_heading_level_preserved():
    """Pre-existing heading_level is not overwritten by document-order fallback."""
    elements = [
        Title("First", metadata=ElementMetadata(page_number=1)),
        Title("Second", metadata=ElementMetadata(page_number=1, heading_level=2)),
    ]
    infer_heading_levels_by_document_order(elements)
    assert elements[0].metadata.heading_level == 1
    assert elements[1].metadata.heading_level == 2


def test_infer_heading_levels_empty_list():
    """Empty element list returns empty list."""
    result = infer_heading_levels([], filename=None, file=None)
    assert result == []


def test_infer_heading_levels_single_title():
    """Single title gets heading_level 1."""
    elements = [Title("Sole", metadata=ElementMetadata(page_number=1))]
    result = infer_heading_levels(
        elements, filename=None, file=None, use_outline=False, use_font_analysis=True
    )
    assert len(result) == 1
    assert result[0].metadata.heading_level == 1


def test_outline_level_above_5_clamped_to_h6():
    """Outline level > 5 is clamped to heading_level 6 (H6)."""
    outline_entries = [
        {"title": "Deep", "level": 5, "page": 1},
        {"title": "Deeper", "level": 10, "page": 1},
    ]
    elements = [
        Title("Deep", metadata=ElementMetadata(page_number=1)),
        Title("Deeper", metadata=ElementMetadata(page_number=1)),
    ]
    infer_heading_levels_from_outline(elements, outline_entries)
    assert elements[0].metadata.heading_level == 6  # level 5 + 1 = 6
    assert elements[1].metadata.heading_level == 6  # level 10 + 1 clamped to 6
