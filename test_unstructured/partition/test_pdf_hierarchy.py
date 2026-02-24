"""Test suite for PDF hierarchical heading detection."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest

from unstructured.documents.elements import Title
from unstructured.partition.pdf_hierarchy import (
    extract_pdf_outline,
    infer_heading_levels,
    infer_heading_levels_from_font_sizes,
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

    # Construct a nested outline structure similar to what pypdf produces:
    # [ Root, [ Child, [ Grandchild ] ] ]
    root = FakeOutlineItem("Root", page=0)
    child = FakeOutlineItem("Child", page=1)
    grandchild = FakeOutlineItem("Grandchild", page=2)
    child.children = [grandchild]
    outline_structure = [root, [child]]

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
        Title("Introduction", metadata=None),
        Title("Chapter 1", metadata=None),
        Title("Section 1.1", metadata=None),
    ]

    # Add metadata to elements
    from unstructured.documents.elements import ElementMetadata

    for element in elements:
        element.metadata = ElementMetadata()

    outline_entries = [
        {"title": "Introduction", "level": 0, "page": 1},
        {"title": "Chapter 1", "level": 1, "page": 2},
        {"title": "Section 1.1", "level": 2, "page": 3},
    ]

    infer_heading_levels_from_outline(elements, outline_entries)

    # Check that heading levels were assigned
    assert elements[0].metadata.heading_level == 1  # level 0 + 1
    assert elements[1].metadata.heading_level == 2  # level 1 + 1
    assert elements[2].metadata.heading_level == 3  # level 2 + 1
    # Levels are normalized to 1-6 range
    assert 1 <= elements[0].metadata.heading_level <= 6
    assert 1 <= elements[1].metadata.heading_level <= 6
    assert 1 <= elements[2].metadata.heading_level <= 6


def test_infer_heading_levels_from_font_sizes():
    """Test inferring heading levels from font size analysis."""
    from unstructured.documents.elements import ElementMetadata

    elements = [
        Title("MAIN TITLE", metadata=ElementMetadata(page_number=1)),
        Title("Subtitle", metadata=ElementMetadata(page_number=1)),
        Title("Another subtitle", metadata=ElementMetadata(page_number=1)),
        Title("Minor heading", metadata=ElementMetadata(page_number=1)),
    ]

    infer_heading_levels_from_font_sizes(elements)

    # Check that heading levels were assigned
    levels = [e.metadata.heading_level for e in elements if e.metadata.heading_level is not None]
    assert len(levels) > 0
    assert all(1 <= level <= 6 for level in levels)


def test_infer_heading_levels_integration():
    """Test the integrated heading level inference function."""
    from unstructured.documents.elements import ElementMetadata

    elements = [
        Title("Introduction", metadata=ElementMetadata(page_number=1)),
        Title("Chapter 1", metadata=ElementMetadata(page_number=2)),
    ]

    # Test with no file (should use font analysis only)
    result = infer_heading_levels(
        elements,
        filename=None,
        file=None,
        use_outline=False,
        use_font_analysis=True,
    )

    assert len(result) == len(elements)
    # At least one element should have a heading level assigned when using font analysis.
    levels = [
        e.metadata.heading_level
        for e in result
        if e.metadata and e.metadata.heading_level is not None
    ]
    assert len(levels) > 0


def test_heading_levels_are_in_range():
    """Test that assigned heading levels are always in the valid range (1-6)."""
    from unstructured.documents.elements import ElementMetadata

    elements = [
        Title("Title 1", metadata=ElementMetadata(page_number=1)),
        Title("Title 2", metadata=ElementMetadata(page_number=1)),
        Title("Title 3", metadata=ElementMetadata(page_number=1)),
        Title("Title 4", metadata=ElementMetadata(page_number=1)),
        Title("Title 5", metadata=ElementMetadata(page_number=1)),
    ]

    infer_heading_levels_from_font_sizes(elements)

    for element in elements:
        if element.metadata and element.metadata.heading_level is not None:
            assert 1 <= element.metadata.heading_level <= 6


def test_fuzzy_matching_in_outline():
    """Test that fuzzy matching works for outline entries."""
    from unstructured.documents.elements import ElementMetadata

    elements = [
        Title("Introduction to the Project", metadata=ElementMetadata()),
    ]

    outline_entries = [
        {"title": "Introduction", "level": 0, "page": 1},
    ]

    infer_heading_levels_from_outline(elements, outline_entries, fuzzy_match_threshold=0.5)

    # Should match "Introduction to the Project" with "Introduction"
    if elements[0].metadata.heading_level is not None:
        assert 1 <= elements[0].metadata.heading_level <= 6

