# pyright: reportPrivateUsage=false

"""Regression and characterization tests for table isolation during chunking (issue #3921).

`Table` (and `TableChunk`, which subclasses `Table`) must never share a pre-chunk with unrelated
text elements, so downstream logic can emit standalone table chunks instead of `CompositeElement`
wrapping mixed content.
"""

from __future__ import annotations

from typing import Callable

import pytest

from unstructured.chunking.base import (
    ChunkingOptions,
    PreChunk,
    PreChunkBuilder,
    PreChunkCombiner,
    PreChunker,
)
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    CompositeElement,
    ElementMetadata,
    Table,
    TableChunk,
    Text,
    Title,
)


class DescribeTableIsolationPreChunkBuilder:
    """`PreChunkBuilder` must keep every table-family element in its own pre-chunk."""

    @pytest.mark.parametrize(
        ("preamble", "make_table"),
        [
            (Text("Short preamble."), lambda: Table("H\nC")),
            (Text("Short preamble."), lambda: TableChunk(text="x", metadata=ElementMetadata())),
        ],
    )
    def it_refuses_to_append_a_table_after_any_other_element(
        self, preamble: Text, make_table: Callable[[], Table]
    ):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=500))
        builder.add_element(preamble)

        assert not builder.will_fit(make_table())

    @pytest.mark.parametrize(
        "trailing",
        [
            Text("Follow-up paragraph."),
            Title("Next section"),
        ],
    )
    def it_refuses_to_append_a_non_table_after_a_table(self, trailing: Text | Title):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=500))
        builder.add_element(Table("Heading\nCell"))

        assert not builder.will_fit(trailing)

    def it_allows_only_a_table_when_the_builder_is_empty(self):
        builder = PreChunkBuilder(opts=ChunkingOptions())
        assert builder.will_fit(Table("Heading\nCell text"))

    def it_allows_text_after_flush_even_if_previous_pre_chunk_was_a_table(self):
        opts = ChunkingOptions(max_characters=200)
        builder = PreChunkBuilder(opts=opts)
        builder.add_element(Table("Heading\nCell text"))
        list(builder.flush())  # clears builder state

        assert builder.will_fit(Text("Fresh start after table pre-chunk."))


class DescribeTableIsolationPreChunkStream:
    """End-to-end pre-chunk segmentation from `PreChunker.iter_pre_chunks`."""

    def it_emits_a_table_only_pre_chunk_between_text_blocks(self):
        elements = [
            Title("Section A"),
            Text("Narrative before the table."),
            Table("Col1\nCell A"),
            Text("Narrative after the table."),
        ]
        # -- `new_after_n_chars=0` forces one element per pre-chunk (deterministic layout) --
        opts = ChunkingOptions(max_characters=500, new_after_n_chars=0)

        pre_chunks = list(PreChunker.iter_pre_chunks(elements, opts=opts))

        assert len(pre_chunks) == 4
        assert pre_chunks[0]._elements == [Title("Section A")]
        assert pre_chunks[1]._elements == [Text("Narrative before the table.")]
        assert pre_chunks[2]._elements == [Table("Col1\nCell A")]
        assert pre_chunks[3]._elements == [Text("Narrative after the table.")]

    def it_emits_one_pre_chunk_per_table_when_multiple_tables_are_adjacent(self):
        elements = [
            Table("T1\nA"),
            Table("T2\nB"),
            Text("Closing text."),
        ]
        opts = ChunkingOptions(max_characters=500)

        pre_chunks = list(PreChunker.iter_pre_chunks(elements, opts=opts))

        assert len(pre_chunks) == 3
        assert pre_chunks[0]._elements == [Table("T1\nA")]
        assert pre_chunks[1]._elements == [Table("T2\nB")]
        assert pre_chunks[2]._elements == [Text("Closing text.")]


class DescribeTableIsolationPreChunkCombiner:
    """`PreChunkCombiner` must not stitch table pre-chunks onto text neighbors."""

    def it_keeps_a_table_pre_chunk_separate_when_combining_is_enabled(self):
        opts = ChunkingOptions(max_characters=500, combine_text_under_n_chars=500)
        stream = [
            PreChunk([Text("Hello world.")], overlap_prefix="", opts=opts),
            PreChunk([Table("H\nC")], overlap_prefix="", opts=opts),
            PreChunk([Text("Goodbye world.")], overlap_prefix="", opts=opts),
        ]

        combined = list(PreChunkCombiner(stream, opts=opts).iter_combined_pre_chunks())

        assert len(combined) == 3
        assert combined[0]._elements == [Text("Hello world.")]
        assert combined[1]._elements == [Table("H\nC")]
        assert combined[2]._elements == [Text("Goodbye world.")]


class DescribeTableIsolationOrderingGuarantees:
    """Invariants that should hold for any future refactor of table isolation."""

    def it_preserves_global_element_order_in_pre_chunks(self):
        elements = [
            Text("alpha"),
            Table("T\n1"),
            Text("beta"),
            Table("T\n2"),
            Title("gamma"),
        ]
        opts = ChunkingOptions(max_characters=500, new_after_n_chars=0)
        flat = [e for pc in PreChunker.iter_pre_chunks(elements, opts=opts) for e in pc._elements]

        assert flat == elements

    def it_preserves_global_element_order_in_chunk_elements_output(self):
        elements = [
            Title("Intro"),
            Text("Body before."),
            Table("K\nV"),
            Text("Body after."),
        ]
        chunks = chunk_elements(elements, max_characters=500, new_after_n_chars=0)
        # -- flatten chunk element categories in stream order (table chunks are atomic) --
        categories = [c.category for c in chunks]

        assert categories == [
            "CompositeElement",
            "CompositeElement",
            "Table",
            "CompositeElement",
        ]


class DescribeTableIsolationChunkElements:
    """`chunk_elements` (basic strategy) should emit `Table`/`TableChunk`, not mixed composites."""

    def it_does_not_wrap_a_table_and_surrounding_text_in_one_composite_element(self):
        elements = [
            Title("Report"),
            Text("Short intro."),
            Table("Key\nValue"),
            Text("Short outro."),
        ]
        chunks = chunk_elements(
            elements,
            max_characters=500,
            new_after_n_chars=0,
        )

        assert len(chunks) == 4
        assert isinstance(chunks[0], CompositeElement)
        assert isinstance(chunks[1], CompositeElement)
        assert isinstance(chunks[2], Table)
        assert isinstance(chunks[3], CompositeElement)
        assert "Key" in chunks[2].text or "Value" in chunks[2].text

    def it_yields_distinct_chunks_for_two_tables_in_a_row(self):
        elements = [
            Table("T1\nA"),
            Table("T2\nB"),
        ]
        chunks = chunk_elements(elements, max_characters=500)

        assert len(chunks) == 2
        assert all(isinstance(c, Table) for c in chunks)

    def it_still_isolates_a_table_even_when_the_window_is_very_large(self):
        """Regression: isolation is a semantic rule, not a size heuristic."""
        elements = [
            Text("x"),
            Table("tiny"),
            Text("y"),
        ]
        chunks = chunk_elements(elements, max_characters=50_000, new_after_n_chars=10_000)

        table_chunks = [c for c in chunks if isinstance(c, Table)]
        composite_chunks = [c for c in chunks if isinstance(c, CompositeElement)]

        assert len(table_chunks) == 1
        assert len(composite_chunks) == 2
        assert "tiny" in table_chunks[0].text

    def it_never_produces_a_composite_element_that_lists_a_table_in_orig_elements(
        self,
    ):
        """`CompositeElement` chunks come from `_Chunker`, not `_TableChunker`."""
        elements = [
            Text("preamble"),
            Table("H\nC"),
            Text("post"),
        ]
        chunks = chunk_elements(
            elements,
            max_characters=400,
            new_after_n_chars=0,
            include_orig_elements=True,
        )

        composites = [c for c in chunks if isinstance(c, CompositeElement)]
        for comp in composites:
            orig = comp.metadata.orig_elements or []
            assert not any(isinstance(e, Table) for e in orig)


class DescribeTableIsolationOverlapAll:
    """With overlap_all=True, overlap must not cross table / narrative boundaries."""

    def it_does_not_prefix_table_chunk_with_prior_text_overlap(self):
        """Regression: pre-chunk overlap_tail must not become table's overlap_prefix."""
        elements = [Text("Alpha beta gamma delta."), Table("H\nC")]
        chunks = chunk_elements(
            elements,
            max_characters=500,
            new_after_n_chars=0,
            overlap=5,
            overlap_all=True,
        )

        table_chunks = [c for c in chunks if isinstance(c, Table)]
        assert len(table_chunks) == 1
        t = table_chunks[0].text or ""
        assert "Alpha" not in t
        assert "elta" not in t  # tail of "delta" leaked in buggy overlap

    def it_does_not_prefix_text_after_table_with_table_overlap(self):
        elements = [Table("H\nC"), Text("Omega sigma tau upsilon.")]
        chunks = chunk_elements(
            elements,
            max_characters=500,
            new_after_n_chars=0,
            overlap=5,
            overlap_all=True,
        )

        composites = [c for c in chunks if isinstance(c, CompositeElement)]
        assert len(composites) == 1
        assert composites[0].text.startswith("Omega")
        assert "H" not in composites[0].text[:20]

    def it_chunk_by_title_respects_same_overlap_boundaries(self):
        elements = [
            Title("Section"),
            Text("Alpha beta gamma delta."),
            Table("H\nC"),
            Text("Omega sigma tau upsilon."),
        ]
        chunks = chunk_by_title(
            elements,
            max_characters=500,
            new_after_n_chars=0,
            overlap=5,
            overlap_all=True,
            combine_text_under_n_chars=0,
        )

        table_chunks = [c for c in chunks if isinstance(c, Table)]
        assert len(table_chunks) == 1
        assert "Alpha" not in (table_chunks[0].text or "")
        assert "elta" not in (table_chunks[0].text or "")

        omega_composites = [
            c for c in chunks if isinstance(c, CompositeElement) and "Omega" in (c.text or "")
        ]
        assert len(omega_composites) == 1
        assert omega_composites[0].text.startswith("Omega")
