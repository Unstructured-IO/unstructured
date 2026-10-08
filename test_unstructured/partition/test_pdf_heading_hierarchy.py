"""Tests for unstructured.partition.pdf_heading_hierarchy."""

from __future__ import annotations

from typing import Any, cast

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.coordinates import PixelSpace
from unstructured.documents.elements import CoordinatesMetadata, ElementMetadata, Title
from unstructured.partition.pdf_heading_hierarchy import (
    _apply_font_size_levels,
    _apply_outline_levels,
    _best_match,
    _open_reader,
    infer_heading_levels,
)


class _FakeBox:
    def __init__(self, width: float = 600, height: float = 800) -> None:
        self.width = width
        self.height = height


class _FakePage:
    def __init__(self) -> None:
        self.cropbox = _FakeBox()


class _FakeDestination:
    def __init__(
        self,
        title: str,
        *,
        page_index: int | None,
        left: float | None = None,
        top: float | None = None,
    ) -> None:
        self.title = title
        self.page_index = page_index
        self.left = left
        self.top = top
        self.right = None
        self.bottom = None
        self.page = page_index


class _FakeReader:
    def __init__(self, outline: list[object]) -> None:
        self.outline = outline
        self.pages = [_FakePage()]

    def get_destination_page_number(self, destination: _FakeDestination) -> int:
        return destination.page_index if destination.page_index is not None else -1


def _title_with_bbox(text: str, y1: float, y2: float) -> Title:
    title = Title(text)
    title.metadata = ElementMetadata(
        page_number=1,
        coordinates=CoordinatesMetadata(
            points=((100, y1), (100, y2), (250, y2), (250, y1)),
            system=PixelSpace(width=600, height=800),
        ),
    )
    return title


class Describe_best_match:
    def it_picks_strongest_match_not_first(self):
        """Prevents PR #4222 regression: greedy early-break selecting wrong match."""
        t1 = Title("Part I Overview")
        t2 = Title("Part II Details")
        best, ratio = _best_match("Part II Details", [t1, t2])
        assert best is t2
        assert ratio == 1.0

    def it_skips_already_assigned_titles(self):
        t1 = Title("Introduction")
        t1.metadata.category_depth = 0
        t2 = Title("Introduction")
        best, _ = _best_match("Introduction", [t1, t2])
        assert best is t2


class Describe_apply_outline_levels:
    def it_matches_on_correct_page(self):
        """Prevents PR #4222 regression: 0-based vs 1-based page mismatch."""
        reader = _open_reader(filename=example_doc_path("pdf/DA-1p.pdf"))
        assert reader is not None
        # Title on page 1 should match; title on wrong page should not
        t_right_page = Title("Codex DAO")
        t_right_page.metadata = ElementMetadata(page_number=1)
        t_wrong_page = Title("Codex DAO")
        t_wrong_page.metadata = ElementMetadata(page_number=999)
        matched = _apply_outline_levels([t_right_page, t_wrong_page], reader)
        assert matched >= 1
        assert t_right_page.metadata.category_depth == 0

    def it_uses_outline_destination_when_same_title_repeats_on_same_page(self):
        upper_title = _title_with_bbox("Introduction", y1=90, y2=120)
        lower_title = _title_with_bbox("Introduction", y1=290, y2=320)
        reader = cast(
            Any,
            _FakeReader(
                outline=[
                    _FakeDestination("Introduction", page_index=0, left=100, top=700),
                    [_FakeDestination("Introduction", page_index=0, left=100, top=500)],
                ],
            ),
        )

        matched = _apply_outline_levels([lower_title, upper_title], reader)

        assert matched == 2
        assert upper_title.metadata.category_depth == 0
        assert lower_title.metadata.category_depth == 1

    def it_skips_external_outline_entries(self):
        title = _title_with_bbox("External Resource", y1=90, y2=120)
        reader = cast(
            Any,
            _FakeReader(
                outline=[
                    _FakeDestination("External Resource", page_index=None, left=100, top=700),
                ],
            ),
        )

        matched = _apply_outline_levels([title], reader)

        assert matched == 0
        assert title.metadata.category_depth is None


class Describe_apply_font_size_levels:
    def it_does_not_overwrite_existing_depths(self):
        t1 = Title("Introduction")
        t1.metadata = ElementMetadata(page_number=1, category_depth=5)
        _apply_font_size_levels([t1], filename=example_doc_path("pdf/layout-parser-paper.pdf"))
        assert t1.metadata.category_depth == 5


class Describe_infer_heading_levels:
    def it_handles_missing_file_gracefully(self):
        t1 = Title("Heading")
        t1.metadata = ElementMetadata(page_number=1)
        result = infer_heading_levels([t1])
        assert result is not None
        assert t1.metadata.category_depth is None

    def it_works_with_file_object(self):
        t1 = Title("Codex DAO")
        t1.metadata = ElementMetadata(page_number=1)
        with open(example_doc_path("pdf/DA-1p.pdf"), "rb") as f:
            infer_heading_levels([t1], file=f)
        assert t1.metadata.category_depth == 0


class Describe_partition_pdf_end_to_end:
    """End-to-end tests calling partition_pdf() and verifying category_depth."""

    def it_assigns_outline_depths_via_fast_strategy(self):
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(example_doc_path("pdf/DA-1p.pdf"), strategy="fast")
        titles = {
            el.text.strip(): el.metadata.category_depth for el in elements if el.category == "Title"
        }
        assert titles["MAIN GAME"] == 1
        assert titles["CREATURES"] == 2
        assert titles["Abomination"] == 3

    def it_assigns_font_size_depths_for_pdf_without_outline(self):
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(example_doc_path("pdf/loremipsum-flat.pdf"), strategy="fast")
        titles = [el for el in elements if el.category == "Title"]
        for t in titles:
            if t.metadata.category_depth is not None:
                assert 0 <= t.metadata.category_depth <= 5

    def it_does_not_set_depths_on_non_title_elements(self):
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(example_doc_path("pdf/DA-1p.pdf"), strategy="fast")
        non_titles = [el for el in elements if el.category != "Title"]
        for el in non_titles:
            assert el.metadata.category_depth is None
