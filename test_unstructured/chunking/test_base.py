# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.chunking.base` module."""

from __future__ import annotations

from typing import Any, Sequence

import pytest
from lxml.html import fragment_fromstring

from unstructured.chunking.base import (
    ChunkingOptions,
    PreChunk,
    PreChunkBuilder,
    PreChunkCombiner,
    PreChunker,
    _CellAccumulator,
    _Chunker,
    _HtmlTableSplitter,
    _PreChunkAccumulator,
    _RowAccumulator,
    _TableChunker,
    _TextSplitter,
    is_on_next_page,
    is_title,
)
from unstructured.common.html_table import HtmlCell, HtmlRow, HtmlTable
from unstructured.documents.elements import (
    CheckBox,
    CompositeElement,
    Element,
    ElementMetadata,
    PageBreak,
    Table,
    TableChunk,
    Text,
    Title,
)

# ================================================================================================
# CHUNKING OPTIONS
# ================================================================================================


class DescribeChunkingOptions:
    """Unit-test suite for `unstructured.chunking.base.ChunkingOptions` objects."""

    @pytest.mark.parametrize("max_characters", [0, -1, -42])
    def it_rejects_max_characters_not_greater_than_zero(self, max_characters: int):
        with pytest.raises(
            ValueError,
            match=f"'max_characters' argument must be > 0, got {max_characters}",
        ):
            ChunkingOptions(max_characters=max_characters)._validate()

    def it_does_not_complain_when_specifying_max_characters_by_itself(self):
        """Caller can specify `max_characters` arg without specifying any others.

        In particular, When `combine_text_under_n_chars` is not specified it defaults to the value
        of `max_characters`; it has no fixed default value that can be greater than `max_characters`
        and trigger an exception.
        """
        try:
            ChunkingOptions(max_characters=50)._validate()
        except ValueError:
            pytest.fail("did not accept `max_characters` as option by itself")

    @pytest.mark.parametrize(
        ("combine_text_under_n_chars", "expected_value"), [(None, 0), (42, 42)]
    )
    def it_accepts_combine_text_under_n_chars_in_constructor_but_defaults_to_no_combining(
        self, combine_text_under_n_chars: int | None, expected_value: int
    ):
        """Subclasses can store `combine_text_under_n_chars` but must validate and enable it.

        The `combine_text_under_n_chars` option is not used by all chunkers and its behavior can
        differ between subtypes. It is present in and stored by the contructur but it defaults to
        `0` (no pre-chunk combining) and must be overridden by subclasses to give it the desired
        behavior.
        """
        opts = ChunkingOptions(combine_text_under_n_chars=combine_text_under_n_chars)
        assert opts.combine_text_under_n_chars == expected_value

    @pytest.mark.parametrize(
        ("kwargs", "expected_value"),
        [
            ({"include_orig_elements": True}, True),
            ({"include_orig_elements": False}, False),
            ({"include_orig_elements": None}, True),
            ({}, True),
        ],
    )
    def it_knows_whether_to_include_orig_elements_in_the_chunk_metadata(
        self, kwargs: dict[str, Any], expected_value: bool
    ):
        assert ChunkingOptions(**kwargs).include_orig_elements is expected_value

    @pytest.mark.parametrize("n_chars", [-1, -42])
    def it_rejects_new_after_n_chars_for_n_less_than_zero(self, n_chars: int):
        with pytest.raises(
            ValueError,
            match=f"'new_after_n_chars' argument must be >= 0, got {n_chars}",
        ):
            ChunkingOptions(new_after_n_chars=n_chars)._validate()

    def it_rejects_overlap_not_less_than_max_characters(self):
        with pytest.raises(
            ValueError,
            match="'overlap' argument must be less than `max_characters`, got 300 >= 200",
        ):
            ChunkingOptions(max_characters=200, overlap=300)._validate()

    def it_does_not_complain_when_specifying_new_after_n_chars_by_itself(self):
        """Caller can specify `new_after_n_chars` arg without specifying any other options."""
        opts = ChunkingOptions(new_after_n_chars=200)
        try:
            opts._validate()
        except ValueError:
            pytest.fail("did not accept `new_after_n_chars` as option by itself")

        assert opts.soft_max == 200

    def it_accepts_0_for_new_after_n_chars_to_put_each_element_into_its_own_chunk(self):
        """Specifying `new_after_n_chars=0` places each element into its own pre-chunk.

        This puts each element into its own chunk, although long chunks are still split.
        """
        opts = ChunkingOptions(new_after_n_chars=0)
        opts._validate()

        assert opts.soft_max == 0

    def it_silently_accepts_new_after_n_chars_greater_than_maxchars(self):
        """`new_after_n_chars` > `max_characters` doesn't affect chunking behavior.

        So rather than raising an exception or warning, we just cap that value at `max_characters`
        which is the behavioral equivalent.
        """
        opts = ChunkingOptions(max_characters=444, new_after_n_chars=555)
        try:
            opts._validate()
        except ValueError:
            pytest.fail("did not accept `new_after_n_chars` greater than `max_characters`")

        assert opts.soft_max == 444

    def it_knows_how_much_overlap_to_apply_to_split_chunks(self):
        assert ChunkingOptions(overlap=10).overlap == 10

    def and_it_uses_the_same_value_for_inter_chunk_overlap_when_asked_to_overlap_all_chunks(self):
        assert ChunkingOptions(overlap=10, overlap_all=True).inter_chunk_overlap == 10

    def but_it_does_not_overlap_pre_chunks_by_default(self):
        assert ChunkingOptions(overlap=10).inter_chunk_overlap == 0

    def it_knows_the_text_separator_string(self):
        assert ChunkingOptions().text_separator == "\n\n"


# ================================================================================================
# PRE-CHUNKER
# ================================================================================================


class DescribePreChunker:
    """Unit-test suite for `unstructured.chunking.base.PreChunker` objects."""

    def it_gathers_elements_into_pre_chunks_respecting_the_specified_chunk_size(self):
        elements = [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet, consectetur adipiscing elit."),
            Text("Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."),
            Title("Ut Enim"),
            Text("Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi."),
            Text("Ut aliquip ex ea commodo consequat."),
            CheckBox(),
        ]

        opts = ChunkingOptions(max_characters=150, new_after_n_chars=65)

        pre_chunk_iter = PreChunker.iter_pre_chunks(elements, opts=opts)

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet, consectetur adipiscing elit."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Text("Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Ut Enim"),
            Text("Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [Text("Ut aliquip ex ea commodo consequat."), CheckBox()]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)


class DescribePreChunkBuilder:
    """Unit-test suite for `unstructured.chunking.base.PreChunkBuilder`."""

    def it_is_empty_on_construction(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=50))

        assert builder._text_length == 0
        assert builder._remaining_space == 50

    def it_accumulates_elements_added_to_it(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=150))

        builder.add_element(Title("Introduction"))
        assert builder._text_length == 12
        assert builder._remaining_space == 136

        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        )
        assert builder._text_length == 112
        assert builder._remaining_space == 36

    def it_will_fit_an_oversized_element_when_empty(self):
        builder = PreChunkBuilder(opts=ChunkingOptions())
        assert builder.will_fit(Text("abcd " * 200))

    @pytest.mark.parametrize(
        ("existing_element", "next_element"),
        [
            (Text("abcd"), Text("abcd " * 200)),
            (Table("Heading\nCell text"), Text("abcd " * 200)),
        ],
    )
    def but_not_when_it_already_contains_an_element(
        self, existing_element: Element, next_element: Element
    ):
        builder = PreChunkBuilder(opts=ChunkingOptions())
        builder.add_element(existing_element)

        assert not builder.will_fit(next_element)

    @pytest.mark.parametrize("element", [Text("abcd"), Table("Fruits\nMango")])
    def it_will_accept_another_element_that_fits_when_it_already_contains_a_table(
        self, element: Element
    ):
        builder = PreChunkBuilder(opts=ChunkingOptions())
        builder.add_element(Table("Heading\nCell text"))

        assert builder.will_fit(element)

    def it_will_not_fit_an_element_when_it_already_exceeds_the_soft_maxlen(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=100, new_after_n_chars=50))
        builder.add_element(
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")  # 55-chars
        )

        assert not builder.will_fit(Text("In rhoncus ipsum."))

    def and_it_will_not_fit_an_element_when_that_would_cause_it_to_exceed_the_hard_maxlen(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=100))
        builder.add_element(
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")  # 55-chars
        )

        # -- 55 + 2 (separator) + 44 == 101 --
        assert not builder.will_fit(
            Text("In rhoncus ipsum sed lectus portos volutpat.")  # 44-chars
        )

    def but_it_will_fit_an_element_that_fits(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=100))
        builder.add_element(
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")  # 55-chars
        )

        # -- 55 + 2 (separator) + 43 == 100 --
        assert builder.will_fit(Text("In rhoncus ipsum sed lectus porto volutpat."))  # 43-chars

    def it_generates_a_PreChunk_when_flushed_and_resets_itself_to_empty(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=150))
        builder.add_element(Title("Introduction"))
        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        )

        pre_chunk = next(builder.flush())

        # -- pre-chunk builder was reset before the yield, such that the iterator does not need to
        # -- be exhausted before clearing out the old elements and a new pre-chunk can be
        # -- accumulated immediately (first `next()` call is required however, to advance to the
        # -- yield statement).
        assert builder._text_length == 0
        assert builder._remaining_space == 150
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Introduction"),
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        ]

    def but_it_does_not_generate_a_pre_chunk_on_flush_when_empty(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=150))

        pre_chunks = list(builder.flush())

        assert pre_chunks == []
        assert builder._text_length == 0
        assert builder._remaining_space == 150

    def it_computes_overlap_from_each_pre_chunk_and_applies_it_to_the_next(self):
        opts = ChunkingOptions(overlap=15, overlap_all=True)
        builder = PreChunkBuilder(opts=opts)

        builder.add_element(Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."))
        pre_chunk = list(builder.flush())[0]

        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._text == "Lorem ipsum dolor sit amet consectetur adipiscing elit."

        builder.add_element(Table("In rhoncus ipsum sed lectus porta volutpat."))
        pre_chunk = list(builder.flush())[0]

        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._text == "dipiscing elit.\n\nIn rhoncus ipsum sed lectus porta volutpat."

        builder.add_element(Text("Donec semper facilisis metus finibus."))
        pre_chunk = list(builder.flush())[0]

        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._text == "porta volutpat.\n\nDonec semper facilisis metus finibus."

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=50))
        builder.add_element(Text("abcde"))
        builder.add_element(Text("fghij"))

        # -- ._text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert builder._text_length == 12
        # -- ._remaining_space is reduced by the length (2) of the trailing separator which would
        # -- go between the current text and that of the next element if one was added.
        # -- So 50 - 12 - 2 = 36 here, not 50 - 12 = 38
        assert builder._remaining_space == 36


# ================================================================================================
# PRE-CHUNK SUBTYPES
# ================================================================================================


class DescribePreChunk:
    """Unit-test suite for `unstructured.chunking.base.PreChunk` objects."""

    @pytest.mark.parametrize(
        ("overlap_pfx", "texts", "other_overlap_pfx", "other_texts", "expected_value"),
        [
            # -- same elements, and overlap-prefix --
            ("foo", ["bar", "baz"], "foo", ["bar", "baz"], True),
            # -- same elements, no overlap-prefix --
            ("", ["bar", "baz"], "", ["bar", "baz"], True),
            # -- same elements, different overlap-prefix --
            ("foo", ["bar", "baz"], "fob", ["bar", "baz"], False),
            # -- different elements, same overlap-prefix --
            ("foo", ["bar", "baz"], "foo", ["bah", "dah"], False),
            # -- different elements, different overlap-prefix --
            ("", ["bar", "baz"], "foo", ["bah", "dah"], False),
        ],
    )
    def it_knows_when_it_is_equal_to_another_PreChunk_instance(
        self,
        overlap_pfx: str,
        texts: list[str],
        other_overlap_pfx: str,
        other_texts: list[str],
        expected_value: bool,
    ):
        opts = ChunkingOptions()
        pre_chunk = PreChunk([Text(t) for t in texts], overlap_prefix=overlap_pfx, opts=opts)
        other_pre_chunk = PreChunk(
            [Text(t) for t in other_texts], overlap_prefix=other_overlap_pfx, opts=opts
        )

        assert (pre_chunk == other_pre_chunk) is expected_value

    def and_it_knows_it_is_NOT_equal_to_an_object_that_is_not_a_PreChunk(self):
        pre_chunk = PreChunk([], overlap_prefix="", opts=ChunkingOptions())
        assert pre_chunk != 42

    @pytest.mark.parametrize(
        ("max_characters", "combine_text_under_n_chars", "expected_value"),
        [
            # Will exactly fit:
            # - Prefix + separator + text = 20 + 2 + 50 = 72 < combine_text_under_n_chars
            # - pre_chunk + separator + next_pre_chunk_text = 72 + 2 + 26 = 100 <= max_characters
            (100, 73, True),
            # -- already exceeds combine_text_under_n_chars threshold --
            (100, 72, False),
            # -- would exceeds hard-max chunking-window threshold --
            (99, 73, False),
        ],
    )
    def it_knows_when_it_can_combine_itself_with_another_PreChunk_instance(
        self, max_characters: int, combine_text_under_n_chars: int, expected_value: bool
    ):
        """This allows `PreChunkCombiner` to operate without knowing `PreChunk` internals."""
        opts = ChunkingOptions(
            max_characters=max_characters,
            combine_text_under_n_chars=combine_text_under_n_chars,
            overlap=20,
            overlap_all=True,
        )
        pre_chunk = PreChunk(
            [Text("Lorem ipsum dolor sit amet consectetur adipiscing.")],  # len == 50
            overlap_prefix="e feugiat efficitur.",  # len == 20
            opts=opts,
        )
        next_pre_chunk = PreChunk(
            [Text("In rhoncus sum sed lectus.")],  # len == 26
            overlap_prefix="sectetur adipiscing.",  # len == 20 but shouldn't come into computation
            opts=opts,
        )

        assert pre_chunk.can_combine(next_pre_chunk) is expected_value

    def it_can_combine_itself_with_another_PreChunk_instance(self):
        """.combine() produces a new pre-chunk by appending the elements of `other_pre-chunk`.

        Note that neither the original or other pre_chunk are mutated.
        """
        opts = ChunkingOptions()
        pre_chunk = PreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ],
            overlap_prefix="feugiat efficitur.",
            opts=opts,
        )
        other_pre_chunk = PreChunk(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            overlap_prefix="porta volupat.",
            opts=opts,
        )

        new_pre_chunk = pre_chunk.combine(other_pre_chunk)

        # -- Combined pre-chunk contains all elements from both, in order. It gets the
        # -- overlap-prefix from the existing pre-chunk and the other overlap-prefix is discarded
        # -- (although it's still in there at the end of the first pre-chunk since that's where it
        # -- came from originally).
        assert new_pre_chunk == PreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            overlap_prefix="feugiat efficitur.",
            opts=opts,
        )
        # -- Neither pre-chunk used for combining is mutated, so we don't have to worry about who
        # -- else may have been given a reference to them.
        assert pre_chunk == PreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ],
            overlap_prefix="feugiat efficitur.",
            opts=opts,
        )
        assert other_pre_chunk == PreChunk(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            overlap_prefix="porta volupat.",
            opts=opts,
        )

    @pytest.mark.parametrize(
        ("text", "expected_value"),
        [
            # -- normally it splits exactly on overlap size  |------- 20 -------|
            ("In rhoncus ipsum sed lectus porta volutpat.", "ctus porta volutpat."),
            # -- but it strips leading and trailing whitespace when the tail includes it --
            ("In rhoncus ipsum sed lect us   portas volutpat.  ", "us portas volutpat."),
        ],
    )
    def it_computes_its_overlap_tail_for_use_in_inter_pre_chunk_overlap(
        self, text: str, expected_value: str
    ):
        pre_chunk = PreChunk(
            [Text(text)], overlap_prefix="", opts=ChunkingOptions(overlap=20, overlap_all=True)
        )
        assert pre_chunk.overlap_tail == expected_value

    @pytest.mark.parametrize(
        ("elements", "overlap_prefix", "expected_value"),
        [
            ([Text("foo"), Text("bar")], "bah da bing.", "bah da bing.\n\nfoo\n\nbar"),
            ([Text("foo"), PageBreak(""), Text("bar")], "da bang.", "da bang.\n\nfoo\n\nbar"),
            ([PageBreak(""), Text("foo")], "bah da boom.", "bah da boom.\n\nfoo"),
            ([Text("foo"), Text("bar"), PageBreak("")], "", "foo\n\nbar"),
        ],
    )
    def it_knows_the_concatenated_text_of_the_pre_chunk_to_help(
        self, elements: list[Text], overlap_prefix: str, expected_value: str
    ):
        """._text is the "joined" text of the pre-chunk elements.

        The text-segment contributed by each element is separated from the next by a blank line
        ("\n\n"). An element that contributes no text does not give rise to a separator.
        """
        pre_chunk = PreChunk(elements, overlap_prefix=overlap_prefix, opts=ChunkingOptions())
        assert pre_chunk._text == expected_value


# ================================================================================================
# CHUNKING HELPER/SPLITTERS
# ================================================================================================


class Describe_Chunker:
    """Unit-test suite for `unstructured.chunking.base._Chunker` objects."""

    def it_generates_a_single_chunk_from_its_elements_if_they_together_fit_in_window(self):
        elements = [
            Title("Introduction"),
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                " lectus porta volutpat.",
            ),
        ]
        opts = ChunkingOptions(max_characters=200, include_orig_elements=True)
        chunker = _Chunker(
            elements,
            text=(
                "e feugiat efficitur.\n\nIntroduction\n\nLorem ipsum dolor sit amet consectetur"
                " adipiscing elit. In rhoncus ipsum sed lectus porta volutpat."
            ),
            opts=opts,
        )

        chunk_iter = chunker._iter_chunks()

        chunk = next(chunk_iter)
        assert chunk == CompositeElement(
            "e feugiat efficitur.\n\nIntroduction\n\nLorem ipsum dolor sit amet consectetur"
            " adipiscing elit. In rhoncus ipsum sed lectus porta volutpat.",
        )
        assert chunk.metadata is chunker._consolidated_metadata
        assert chunk.metadata.orig_elements == elements
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def but_it_generates_split_chunks_when_its_single_element_exceeds_window_size(self):
        # -- Chunk-splitting only occurs when a *single* element is too big to fit in the window.
        # -- The pre-chunker will automatically isolate that element in a pre_chunk of its own.
        text = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor"
            " incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud"
            " exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
        )
        elements = [Text(text)]
        opts = ChunkingOptions(max_characters=200, include_orig_elements=True)
        chunker = _Chunker(elements, text=text, opts=opts)

        chunk_iter = chunker._iter_chunks()

        # -- Note that .metadata.orig_elements is the same single original element, "repeated" for
        # -- each text-split chunk. This behavior emerges without explicit command as a consequence
        # -- of using `._consolidated_metadata` (and `._continuation_metadata` which extends
        # -- `._consolidated_metadata)` for each text-split chunk.
        chunk = next(chunk_iter)
        assert chunk == CompositeElement(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod"
            " tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim"
            " veniam, quis nostrud exercitation ullamco laboris nisi ut"
        )
        assert chunk.metadata is chunker._consolidated_metadata
        assert chunk.metadata.orig_elements == elements
        # --
        chunk = next(chunk_iter)
        assert chunk == CompositeElement("aliquip ex ea commodo consequat.")
        assert chunk.metadata is chunker._continuation_metadata
        assert chunk.metadata.orig_elements == elements
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def and_it_adds_the_is_continuation_flag_for_second_and_later_split_chunks(self):
        # --    |--------------------- 48 ---------------------|
        text = "'Lorem ipsum dolor' means 'Thank you very much'."
        metadata = ElementMetadata(
            category_depth=0,
            filename="foo.docx",
            languages=["lat"],
            parent_id="f87731e0",
        )
        elements = [Text(text, metadata=metadata)]

        chunk_iter = _Chunker.iter_chunks(elements, text, opts=ChunkingOptions(max_characters=20))

        assert [c.metadata.is_continuation for c in chunk_iter] == [None, True, True]

    def but_it_generates_no_chunks_when_the_pre_chunk_contains_no_text(self):
        metadata = ElementMetadata()

        chunk_iter = _Chunker.iter_chunks(
            [PageBreak("  ", metadata=metadata)],
            text="",
            opts=ChunkingOptions(),
        )

        with pytest.raises(StopIteration):
            next(chunk_iter)

    def it_extracts_all_populated_metadata_values_from_the_elements_to_help(self):
        elements = [
            Title(
                "Lorem Ipsum",
                metadata=ElementMetadata(
                    category_depth=0,
                    filename="foo.docx",
                    languages=["lat"],
                    parent_id="f87731e0",
                ),
            ),
            Text(
                "'Lorem ipsum dolor' means 'Thank you very much' in Latin.",
                metadata=ElementMetadata(
                    category_depth=1,
                    filename="foo.docx",
                    image_path="sprite.png",
                    languages=["lat", "eng"],
                ),
            ),
        ]
        text = "Lorem Ipsum\n\n'Lorem ipsum dolor' means 'Thank you very much' in Latin."

        chunker = _Chunker(elements, text=text, opts=ChunkingOptions())

        assert chunker._all_metadata_values == {
            # -- scalar values are accumulated in a list in element order --
            "category_depth": [0, 1],
            # -- all values are accumulated, not only unique ones --
            "filename": ["foo.docx", "foo.docx"],
            # -- list-type fields produce a list of lists --
            "languages": [["lat"], ["lat", "eng"]],
            # -- fields that only appear in some elements are captured --
            "image_path": ["sprite.png"],
            "parent_id": ["f87731e0"],
            # -- A `None` value never appears, neither does a field-name with an empty list --
        }

    def but_it_discards_ad_hoc_metadata_fields_during_consolidation(self):
        metadata = ElementMetadata(
            category_depth=0,
            filename="foo.docx",
            languages=["lat"],
            parent_id="f87731e0",
        )
        metadata.coefficient = 0.62
        metadata_2 = ElementMetadata(
            category_depth=1,
            filename="foo.docx",
            image_path="sprite.png",
            languages=["lat", "eng"],
        )
        metadata_2.quotient = 1.74
        elements = [
            Title("Lorem Ipsum", metadata=metadata),
            Text("'Lorem ipsum dolor' means 'Thank you very much'.", metadata=metadata_2),
        ]
        text = "Lorem Ipsum\n\n'Lorem ipsum dolor' means 'Thank you very much' in Latin."

        chunker = _Chunker(elements, text=text, opts=ChunkingOptions())

        # -- ad-hoc fields "coefficient" and "quotient" do not appear --
        assert chunker._all_metadata_values == {
            "category_depth": [0, 1],
            "filename": ["foo.docx", "foo.docx"],
            "image_path": ["sprite.png"],
            "languages": [["lat"], ["lat", "eng"]],
            "parent_id": ["f87731e0"],
        }

    def and_it_adds_the_pre_chunk_elements_to_metadata_when_so_instructed(self):
        opts = ChunkingOptions(include_orig_elements=True)
        metadata = ElementMetadata(filename="foo.pdf")
        element = Title("Lorem Ipsum", metadata=metadata)
        element_2 = Text("'Lorem ipsum dolor' means 'Thank you very much'.", metadata=metadata)
        elements = [element, element_2]
        text = "Lorem Ipsum\n\n'Lorem ipsum dolor' means 'Thank you very much' in Latin."
        chunker = _Chunker(elements, text=text, opts=opts)

        consolidated_metadata = chunker._consolidated_metadata

        # -- pre-chunk elements are included as metadata --
        orig_elements = consolidated_metadata.orig_elements
        assert orig_elements is not None
        assert orig_elements == [element, element_2]
        # -- and they are the exact instances, not copies --
        assert orig_elements[0] is element
        assert orig_elements[1] is element_2

    def it_forms_ElementMetadata_constructor_kwargs_by_applying_consolidation_strategies(self):
        """._meta_kwargs is used like `ElementMetadata(**self._meta_kwargs)` to construct metadata.

        Only non-None fields should appear in the dict and each field value should be the
        consolidation of the values across the pre_chunk elements.
        """
        elements = [
            PageBreak(""),
            Title(
                "Lorem Ipsum",
                metadata=ElementMetadata(
                    filename="foo.docx",
                    # -- category_depth has DROP strategy so doesn't appear in result --
                    category_depth=0,
                    emphasized_text_contents=["Lorem", "Ipsum"],
                    emphasized_text_tags=["b", "i"],
                    languages=["lat"],
                ),
            ),
            Text(
                "'Lorem ipsum dolor' means 'Thank you very much' in Latin.",
                metadata=ElementMetadata(
                    # -- filename change doesn't happen IRL but demonstrates FIRST strategy --
                    filename="bar.docx",
                    # -- emphasized_text_contents has LIST_CONCATENATE strategy, so "Lorem"
                    # -- appears twice in consolidated-meta (as it should) and length matches
                    # -- that of emphasized_text_tags both before and after consolidation.
                    emphasized_text_contents=["Lorem", "ipsum"],
                    emphasized_text_tags=["i", "b"],
                    # -- languages has LIST_UNIQUE strategy, so "lat(in)" appears only once --
                    languages=["eng", "lat"],
                ),
            ),
        ]
        text = "Lorem Ipsum\n\n'Lorem ipsum dolor' means 'Thank you very much' in Latin."
        chunker = _Chunker(elements, text=text, opts=ChunkingOptions())

        meta_kwargs = chunker._meta_kwargs

        assert meta_kwargs == {
            "filename": "foo.docx",
            "emphasized_text_contents": ["Lorem", "Ipsum", "Lorem", "ipsum"],
            "emphasized_text_tags": ["b", "i", "i", "b"],
            "languages": ["lat", "eng"],
        }

    def it_computes_the_original_elements_list_to_help(self):
        opts = ChunkingOptions(include_orig_elements=True)
        element = Title("Introduction")
        element_2 = Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")
        element_3 = CompositeElement(
            "In rhoncus ipsum sed lectus porta volutpat.",
            metadata=ElementMetadata(orig_elements=[Text("Porta volupat.")]),
        )
        elements = [element, element_2, element_3]
        text = (
            "Introduction\n\nLorem ipsum dolor sit amet consectetur adipiscing elit.\n\nIn"
            " rhoncus ipsum sed lectus porta volutpat."
        )
        chunker = _Chunker(elements, text=text, opts=opts)

        orig_elements = chunker._orig_elements

        # -- all elements of pre-chunk are included --
        assert orig_elements == [element, element_2, element_3]
        # -- orig_elements that are chunks (having orig-elements of their own) are copied and the
        # -- copy is stripped of its `.metadata.orig_elements` to prevent a recursive data
        # -- structure that nests orig_elements within orig_elements.
        assert orig_elements[0] is element
        assert orig_elements[2] is not element_3
        assert orig_elements[2].metadata.orig_elements is None
        # -- computation is only on first call, all chunks get exactly the same orig-elements --
        assert chunker._orig_elements is orig_elements


class Describe_TableChunker:
    """Unit-test suite for `unstructured.chunking.base._TableChunker` objects."""

    def it_uses_its_table_as_the_sole_chunk_when_it_fits_in_the_window(self):
        html_table = (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1 </th><th>Header Col 2 </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lorem ipsum  </td><td>adipiscing   </td></tr>\n"
            "</tbody>\n"
            "</table>"
        )
        text_table = "Header Col 1  Header Col 2\nLorem ipsum   adipiscing"

        chunk_iter = _TableChunker.iter_chunks(
            Table(text_table, metadata=ElementMetadata(text_as_html=html_table)),
            overlap_prefix="ctus porta volutpat.",
            opts=ChunkingOptions(max_characters=175),
        )

        chunk = next(chunk_iter)
        assert isinstance(chunk, Table)
        assert chunk.text == (
            "ctus porta volutpat.\nHeader Col 1  Header Col 2\nLorem ipsum   adipiscing"
        )
        assert chunk.metadata.text_as_html == (
            "<table>"
            "<tr><td>Header Col 1</td><td>Header Col 2</td></tr>"
            "<tr><td>Lorem ipsum</td><td>adipiscing</td></tr>"
            "</table>"
        )
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def but_not_when_the_table_is_is_empty_or_contains_only_whitespace(self):
        html_table = "<table><tr><td/><td>  \t  \n   </td></tr></table>"

        chunk_iter = _TableChunker.iter_chunks(
            Table("  \t  \n  ", metadata=ElementMetadata(text_as_html=html_table)),
            overlap_prefix="volutpat.",
            opts=ChunkingOptions(max_characters=175),
        )

        with pytest.raises(StopIteration):
            next(chunk_iter)

    def and_it_includes_the_original_table_element_in_metadata_when_so_instructed(self):
        table = Table("foo bar", metadata=ElementMetadata(text_as_html="<table>foo bar</table>"))
        opts = ChunkingOptions(include_orig_elements=True)

        chunk_iter = _TableChunker.iter_chunks(table, "", opts)

        chunk = next(chunk_iter)
        assert isinstance(chunk, Table)
        assert chunk.metadata.orig_elements == [table]
        assert chunk.metadata.text_as_html == "<table>foo bar</table>"
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def but_not_when_instructed_not_to(self):
        chunk_iter = _TableChunker.iter_chunks(
            Table("foobar"), "", ChunkingOptions(include_orig_elements=False)
        )

        chunk = next(chunk_iter)

        assert isinstance(chunk, Table)
        assert chunk.metadata.orig_elements is None

    def it_splits_its_table_into_TableChunks_when_the_table_text_exceeds_the_window(self):
        html_table = """\
            <table>
            <thead>
            <tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>
            </thead>
            <tbody>
            <tr><td>Lorem ipsum    </td><td>A Link example</td></tr>
            <tr><td>Consectetur    </td><td>adipiscing elit</td></tr>
            <tr><td>Nunc aliquam   </td><td>id enim nec molestie</td></tr>
            </tbody>
            </table>
        """
        text_table = (
            "Header Col 1   Header Col 2\n"
            "Lorem ipsum    dolor sit amet\n"
            "Consectetur    adipiscing elit\n"
            "Nunc aliquam   id enim nec molestie\n"
            "Vivamus quis   nunc ipsum donec ac fermentum"
        )

        chunk_iter = _TableChunker.iter_chunks(
            Table(text_table, metadata=ElementMetadata(text_as_html=html_table)),
            overlap_prefix="",
            opts=ChunkingOptions(max_characters=100, text_splitting_separators=("\n", " ")),
        )

        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == (
            "Header Col 1 Header Col 2 Lorem ipsum A Link example Consectetur adipiscing elit"
        )
        assert chunk.metadata.text_as_html == (
            "<table>"
            "<tr><td>Header Col 1</td><td>Header Col 2</td></tr>"
            "<tr><td>Lorem ipsum</td><td>A Link example</td></tr>"
            "<tr><td>Consectetur</td><td>adipiscing elit</td></tr>"
            "</table>"
        )
        assert chunk.metadata.is_continuation is None
        # --
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == "Nunc aliquam id enim nec molestie"
        assert chunk.metadata.text_as_html == (
            "<table><tr><td>Nunc aliquam</td><td>id enim nec molestie</td></tr></table>"
        )
        assert chunk.metadata.is_continuation
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def and_it_includes_the_whole_original_Table_in_each_metadata_when_so_instructed(self):
        """Even though text and html are split, the orig_elements metadata is not."""
        table = Table(
            "Header Col 1   Header Col 2\nLorem ipsum   dolor sit amet",
            metadata=ElementMetadata(text_as_html="<table/>"),
        )
        opts = ChunkingOptions(max_characters=30, include_orig_elements=True)

        chunk_iter = _TableChunker.iter_chunks(table, overlap_prefix="", opts=opts)

        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == "Header Col 1   Header Col 2"
        assert chunk.metadata.orig_elements == [table]
        assert not chunk.metadata.is_continuation
        # --
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == "Lorem ipsum   dolor sit amet"
        assert chunk.metadata.orig_elements == [table]
        assert chunk.metadata.is_continuation

    @pytest.mark.parametrize(
        ("text", "overlap_prefix", "expected_value"),
        [
            (
                "In rhoncus ipsum sed lectus porta volutpat.",
                "",
                "In rhoncus ipsum sed lectus porta volutpat.",
            ),
            (
                "In rhoncus ipsum sed lectus porta volutpat.",
                "ctus porta volutpat.",
                "ctus porta volutpat.\nIn rhoncus ipsum sed lectus porta volutpat.",
            ),
        ],
    )
    def it_includes_its_overlap_prefix_in_its_text_when_present(
        self, text: str, overlap_prefix: str, expected_value: str
    ):
        table_chunker = _TableChunker(
            Table(text), overlap_prefix=overlap_prefix, opts=ChunkingOptions()
        )
        assert table_chunker._text_with_overlap == expected_value

    def it_computes_metadata_for_each_chunk_to_help(self):
        table = Table("Lorem ipsum", metadata=ElementMetadata(text_as_html="<table/>"))
        table_chunker = _TableChunker(table, overlap_prefix="", opts=ChunkingOptions())

        metadata = table_chunker._metadata

        assert metadata.text_as_html == "<table/>"
        # -- opts.include_orig_elements is True by default --
        assert metadata.orig_elements == [table]
        # -- it produces a new instance each time it is called so changing one chunk's metadata does
        # -- not change that of any other chunk.
        assert table_chunker._metadata is not metadata

    def but_it_omits_orig_elements_from_metadata_when_so_instructed(self):
        table_chunker = _TableChunker(
            Table("Lorem ipsum", metadata=ElementMetadata(text_as_html="<table/>")),
            overlap_prefix="",
            opts=ChunkingOptions(include_orig_elements=False),
        )

        assert table_chunker._metadata.orig_elements is None

    def it_computes_the_original_elements_list_to_help(self):
        table = Table(
            "Lorem ipsum",
            metadata=ElementMetadata(text_as_html="<table/>", orig_elements=[Table("Lorem Ipsum")]),
        )
        table_chunker = _TableChunker(table, overlap_prefix="", opts=ChunkingOptions())

        orig_elements = table_chunker._orig_elements

        # -- a _TableChunker always has exactly one original (Table) element --
        assert len(orig_elements) == 1
        orig_element = orig_elements[0]
        # -- each item in orig_elements is a copy of the original element so we can mutate it
        # -- without changing user's data.
        assert orig_element == table
        assert orig_element is not table
        # -- it strips any .metadata.orig_elements from each element to prevent a recursive data
        # -- structure
        assert orig_element.metadata.orig_elements is None
        # -- computation is only on first call, all chunks get exactly the same orig-elements --
        assert table_chunker._orig_elements is orig_elements


# ================================================================================================
# HTML SPLITTERS
# ================================================================================================


class Describe_HtmlTableSplitter:
    """Unit-test suite for `unstructured.chunking.base._HtmlTableSplitter`."""

    def it_splits_an_HTML_table_on_whole_row_boundaries_when_possible(self):
        opts = ChunkingOptions(max_characters=(40))
        html_table = HtmlTable.from_html_text(
            """
            <table border="1" class="dataframe">
              <tbody>
                <tr>
                  <td>Stanley
              Cups</td>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td>Team</td>
                  <td>Location</td>
                  <td>Stanley Cups</td>
                </tr>
                <tr>
                  <td>Blues</td>
                  <td>STL</td>
                  <td>1</td>
                </tr>
                <tr>
                  <td>Flyers</td>
                  <td>PHI</td>
                  <td>2</td>
                </tr>
                <tr>
                  <td>Maple Leafs</td>
                  <td>TOR</td>
                  <td>13</td>
                </tr>
              </tbody>
            </table>
            """
        )

        assert list(_HtmlTableSplitter.iter_subtables(html_table, opts)) == [
            (
                "Stanley Cups Team Location Stanley Cups",
                "<table>"
                "<tr><td>Stanley Cups</td><td/><td/></tr>"
                "<tr><td>Team</td><td>Location</td><td>Stanley Cups</td></tr>"
                "</table>",
            ),
            (
                "Blues STL 1 Flyers PHI 2",
                "<table>"
                "<tr><td>Blues</td><td>STL</td><td>1</td></tr>"
                "<tr><td>Flyers</td><td>PHI</td><td>2</td></tr>"
                "</table>",
            ),
            (
                "Maple Leafs TOR 13",
                "<table>" "<tr><td>Maple Leafs</td><td>TOR</td><td>13</td></tr>" "</table>",
            ),
        ]

    def and_it_splits_an_oversized_row_on_an_even_cell_boundary_when_possible(self):
        opts = ChunkingOptions(max_characters=(93))
        html_table = HtmlTable.from_html_text(
            """
            <html><body><table>
              <tr>
                <td>Lorem ipsum dolor sit amet.</td>
                <td>   Consectetur    adipiscing     elit.   </td>
                <td>
                  Laboris nisi ut
                  aliquip ex ea commodo.
                </td>
              </tr>
              <tr>
                <td>Duis</td>
                <td>Dolor</td>
              </tr>
              <tr>
                <td>Duis</td>
                <td>Cillum</td>
              </tr>
            </table></body></html>
            """
        )

        assert list(_HtmlTableSplitter.iter_subtables(html_table, opts)) == [
            (
                "Lorem ipsum dolor sit amet. Consectetur adipiscing elit.",
                "<table><tr>"
                "<td>Lorem ipsum dolor sit amet.</td>"
                "<td>Consectetur adipiscing elit.</td>"
                "</tr></table>",
            ),
            (
                "Laboris nisi ut aliquip ex ea commodo.",
                "<table><tr><td>Laboris nisi ut aliquip ex ea commodo.</td></tr></table>",
            ),
            (
                "Duis Dolor Duis Cillum",
                "<table>"
                "<tr><td>Duis</td><td>Dolor</td></tr>"
                "<tr><td>Duis</td><td>Cillum</td></tr>"
                "</table>",
            ),
        ]

    def and_it_splits_an_oversized_cell_on_an_even_word_boundary(self):
        opts = ChunkingOptions(max_characters=(100))
        html_table = HtmlTable.from_html_text(
            """
            <table>
              <thead>
                <tr>
                  <td>
                    Lorem ipsum dolor sit amet,
                    consectetur adipiscing elit.
                    Sed do eiusmod tempor
                    incididunt ut labore et dolore magna aliqua.
                  </td>
                  <td> Ut enim ad minim veniam.           </td>
                  <td> Quis nostrud exercitation ullamco. </td>
                </tr>
              </thead>
              <tbody>
                <tr><td>Duis aute irure dolor</td></tr>
                <tr><td>In reprehenderit voluptate.</td></tr>
              </tbody>
            </table
            """
        )

        assert list(_HtmlTableSplitter.iter_subtables(html_table, opts)) == [
            (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do",
                "<table>"
                "<tr><td>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do</td></tr>"
                "</table>",
            ),
            (
                "eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                "<table>"
                "<tr><td>eiusmod tempor incididunt ut labore et dolore magna aliqua.</td></tr>"
                "</table>",
            ),
            (
                "Ut enim ad minim veniam. Quis nostrud exercitation ullamco.",
                "<table><tr>"
                "<td>Ut enim ad minim veniam.</td>"
                "<td>Quis nostrud exercitation ullamco.</td>"
                "</tr></table>",
            ),
            (
                "Duis aute irure dolor In reprehenderit voluptate.",
                "<table>"
                "<tr><td>Duis aute irure dolor</td></tr>"
                "<tr><td>In reprehenderit voluptate.</td></tr>"
                "</table>",
            ),
        ]


class Describe_TextSplitter:
    """Unit-test suite for `unstructured.chunking.base._TextSplitter` objects."""

    def it_splits_on_a_preferred_separator_when_it_can(self):
        opts = ChunkingOptions(max_characters=50, text_splitting_separators=("\n", " "), overlap=10)
        split = _TextSplitter(opts)
        text = (
            "Lorem ipsum dolor amet consectetur adipiscing.  \n  "
            "In rhoncus ipsum sed lectus porta."
        )

        s, remainder = split(text)

        # -- trailing whitespace is stripped from split --
        assert s == "Lorem ipsum dolor amet consectetur adipiscing."
        # -- leading whitespace is stripped from remainder
        # -- overlap is separated by single space
        # -- overlap-prefix is computed on arbitrary character boundary
        # -- overlap-prefix len includes space separator (text portion is one less than specified)
        assert remainder == "ipiscing. In rhoncus ipsum sed lectus porta."
        # --
        s, remainder = split(remainder)
        assert s == "ipiscing. In rhoncus ipsum sed lectus porta."
        assert remainder == ""

    def and_it_splits_on_the_next_available_separator_when_the_first_is_not_available(self):
        opts = ChunkingOptions(max_characters=40, text_splitting_separators=("\n", " "), overlap=10)
        split = _TextSplitter(opts)
        text = (
            "Lorem ipsum dolor amet consectetur adipiscing. In rhoncus ipsum sed lectus porta"
            " volutpat."
        )

        s, remainder = split(text)
        assert s == "Lorem ipsum dolor amet consectetur"
        assert remainder == "nsectetur adipiscing. In rhoncus ipsum sed lectus porta volutpat."
        # --
        s, remainder = split(remainder)
        assert s == "nsectetur adipiscing. In rhoncus ipsum"
        assert remainder == "cus ipsum sed lectus porta volutpat."
        # --
        s, remainder = split(remainder)
        assert s == "cus ipsum sed lectus porta volutpat."
        assert remainder == ""

    def and_it_splits_on_an_arbitrary_character_as_a_last_resort(self):
        opts = ChunkingOptions(max_characters=30, text_splitting_separators=("\n", " "), overlap=10)
        split = _TextSplitter(opts)
        text = "Loremipsumdolorametconsecteturadipiscingelit. In rhoncus ipsum sed lectus porta."

        s, remainder = split(text)
        assert s == "Loremipsumdolorametconsectetur"
        assert remainder == "onsecteturadipiscingelit. In rhoncus ipsum sed lectus porta."
        # --
        s, remainder = split(remainder)
        assert s == "onsecteturadipiscingelit. In"
        assert remainder == "gelit. In rhoncus ipsum sed lectus porta."
        # --
        s, remainder = split(remainder)
        assert s == "gelit. In rhoncus ipsum sed"
        assert remainder == "ipsum sed lectus porta."

    @pytest.mark.parametrize(
        "text",
        [
            "Lorem ipsum dolor amet consectetur adipiscing.",  # 46-chars
            "Lorem ipsum dolor.",  # 18-chars
        ],
    )
    def it_does_not_split_a_string_that_is_not_longer_than_maxlen(self, text: str):
        opts = ChunkingOptions(max_characters=46, overlap=10)
        split = _TextSplitter(opts)

        s, remainder = split(text)

        assert s == text
        assert remainder == ""

    def it_fills_the_window_when_falling_back_to_an_arbitrary_character_split(self):
        opts = ChunkingOptions(max_characters=38, overlap=10)
        split = _TextSplitter(opts)
        text = "Loremipsumdolorametconsecteturadipiscingelit. In rhoncus ipsum sed lectus porta."

        s, _ = split(text)

        assert s == "Loremipsumdolorametconsecteturadipisci"
        assert len(s) == 38

    @pytest.mark.parametrize("separators", [("\n", " "), (" ",)])
    def it_strips_whitespace_around_the_split(self, separators: Sequence[str]):
        opts = ChunkingOptions(max_characters=50, text_splitting_separators=separators, overlap=10)
        split = _TextSplitter(opts)
        text = "Lorem ipsum dolor amet consectetur adipiscing.   \n\n In rhoncus ipsum sed lectus."
        #       |-------------------------------------------------^  50-chars

        s, remainder = split(text)

        assert s == "Lorem ipsum dolor amet consectetur adipiscing."
        assert remainder == "ipiscing. In rhoncus ipsum sed lectus."


class Describe_CellAccumulator:
    """Unit-test suite for `unstructured.chunking.base._CellAccumulator`."""

    def it_is_empty_on_construction(self):
        accum = _CellAccumulator(maxlen=100)

        assert accum._cells == []

    def it_accumulates_elements_added_to_it(self):
        td = fragment_fromstring("<td>foobar</td>")
        cell = HtmlCell(td)
        accum = _CellAccumulator(maxlen=100)

        accum.add_cell(cell)

        assert accum._cells == [cell]

    @pytest.mark.parametrize(
        ("cell_html", "expected_value"),
        [
            ("<td/>", True),
            ("<td>Lorem Ipsum.</td>", True),
            ("<td>Lorem Ipsum dolor sit.</td>", True),
            ("<td>Lorem Ipsum dolor sit amet.</td>", False),
        ],
    )
    def it_will_fit_a_cell_with_text_shorter_than_maxlen_when_empty(
        self, cell_html: str, expected_value: bool
    ):
        accum = _CellAccumulator(maxlen=25)
        cell = HtmlCell(fragment_fromstring(cell_html))

        print(f"{cell.text=}")

        assert accum.will_fit(cell) is expected_value

    @pytest.mark.parametrize(
        ("cell_html", "expected_value"),
        [
            ("<td/>", True),  # -- 0 --
            ("<td>Lorem Ipsum.</td>", True),  # -- 12 --
            ("<td>Lorem Ipsum amet.</td>", True),  # -- 17 --
            ("<td>Lorem Ipsum dolor.</td>", False),  # -- 18 --
            ("<td>Lorem Ipsum dolor sit amet.</td>", False),  # -- 27 --
        ],
    )
    def and_it_will_fit_a_cell_with_text_shorter_than_remaining_space_when_not_empty(
        self, cell_html: str, expected_value: bool
    ):
        accum = _CellAccumulator(maxlen=44)
        accum.add_cell(HtmlCell(fragment_fromstring("<td>abcdefghijklmnopqrstuvwxyz</td>")))
        # -- remaining space is 44 - 26 = 18; max new cell text len is 17 --
        cell = HtmlCell(fragment_fromstring(cell_html))

        assert accum.will_fit(cell) is expected_value

    def it_generates_a_TextAndHtml_pair_and_resets_itself_to_empty_when_flushed(self):
        accum = _CellAccumulator(maxlen=100)
        accum.add_cell(HtmlCell(fragment_fromstring("<td>abcde fghij klmno</td>")))

        text, html = next(accum.flush())

        assert text == "abcde fghij klmno"
        assert html == "<table><tr><td>abcde fghij klmno</td></tr></table>"
        assert accum._cells == []

    def and_the_HTML_contains_as_many_cells_as_were_accumulated(self):
        accum = _CellAccumulator(maxlen=100)
        accum.add_cell(HtmlCell(fragment_fromstring("<td>abcde fghij klmno</td>")))
        accum.add_cell(HtmlCell(fragment_fromstring("<td>pqrst uvwxy z</td>")))

        text, html = next(accum.flush())

        assert text == "abcde fghij klmno pqrst uvwxy z"
        assert html == "<table><tr><td>abcde fghij klmno</td><td>pqrst uvwxy z</td></tr></table>"
        assert accum._cells == []

    def but_it_does_not_generate_a_TextAndHtml_pair_when_empty(self):
        accum = _CellAccumulator(maxlen=100)

        with pytest.raises(StopIteration):
            next(accum.flush())


class Describe_RowAccumulator:
    """Unit-test suite for `unstructured.chunking.base._RowAccumulator`."""

    def it_is_empty_on_construction(self):
        accum = _RowAccumulator(maxlen=100)

        assert accum._rows == []

    def it_accumulates_rows_added_to_it(self):
        accum = _RowAccumulator(maxlen=100)
        row = HtmlRow(fragment_fromstring("<tr><td>foo</td><td>bar</td></tr>"))

        accum.add_row(row)

        assert accum._rows == [row]

    @pytest.mark.parametrize(
        ("row_html", "expected_value"),
        [
            ("<tr/>", True),  # -- 0 --
            ("<tr><td/></tr>", True),  # -- 0 --
            ("<tr><td>Lorem Ipsum.</td></tr>", True),  # -- 12 --
            ("<tr><td>Lorem Ipsum dolor sit</td></tr>", True),  # -- 21 --
            ("<tr><td>Lorem</td><td>Sit amet</td></tr>", True),  # -- 14 --
            ("<tr><td>Lorem Ipsum dolor sit amet.</td></tr>", False),  # -- 27 --
            ("<tr><td>Lorem Ipsum</td><td>Dolor sit.</td></tr>", False),  # -- 22 --
        ],
    )
    def it_will_fit_a_row_with_text_shorter_than_maxlen_when_empty(
        self, row_html: str, expected_value: bool
    ):
        accum = _RowAccumulator(maxlen=21)
        row = HtmlRow(fragment_fromstring(row_html))

        assert accum.will_fit(row) is expected_value

    @pytest.mark.parametrize(
        ("row_html", "expected_value"),
        [
            ("<tr/>", True),  # -- 0 --
            ("<tr><td/></tr>", True),  # -- 0 --
            ("<tr><td>Lorem Ipsum.</td></tr>", True),  # -- 12 --
            ("<tr><td>Lorem Ipsum dolor sit</td></tr>", True),  # -- 21 --
            ("<tr><td>Lorem</td><td>Sit amet</td></tr>", True),  # -- 14 --
            ("<tr><td>Lorem Ipsum dolor sit amet.</td></tr>", False),  # -- 27 --
            ("<tr><td>Lorem Ipsum</td><td>Dolor sit.</td></tr>", False),  # -- 22 --
        ],
    )
    def and_it_will_fit_a_row_with_text_shorter_than_remaining_space_when_not_empty(
        self, row_html: str, expected_value: bool
    ):
        """There is no overhead beyond row HTML for additional rows."""
        accum = _RowAccumulator(maxlen=48)
        accum.add_row(HtmlRow(fragment_fromstring("<tr><td>abcdefghijklmnopqrstuvwxyz</td></tr>")))
        # -- remaining space is 48 - 26 = 21 --
        row = HtmlRow(fragment_fromstring(row_html))

        assert accum.will_fit(row) is expected_value

    def it_generates_a_TextAndHtml_pair_and_resets_itself_to_empty_when_flushed(self):
        accum = _RowAccumulator(maxlen=100)
        accum.add_row(HtmlRow(fragment_fromstring("<tr><td>abcde fghij klmno</td></tr>")))

        text, html = next(accum.flush())

        assert text == "abcde fghij klmno"
        assert html == "<table><tr><td>abcde fghij klmno</td></tr></table>"
        assert accum._rows == []

    def and_the_HTML_contains_as_many_rows_as_were_accumulated(self):
        accum = _RowAccumulator(maxlen=100)
        accum.add_row(HtmlRow(fragment_fromstring("<tr><td>abcde fghij klmno</td></tr>")))
        accum.add_row(HtmlRow(fragment_fromstring("<tr><td>pqrst uvwxy z</td></tr>")))

        text, html = next(accum.flush())

        assert text == "abcde fghij klmno pqrst uvwxy z"
        assert html == (
            "<table>"
            "<tr><td>abcde fghij klmno</td></tr>"
            "<tr><td>pqrst uvwxy z</td></tr>"
            "</table>"
        )
        assert accum._rows == []

    def but_it_does_not_generate_a_TextAndHtml_pair_when_empty(self):
        accum = _RowAccumulator(maxlen=100)

        with pytest.raises(StopIteration):
            next(accum.flush())


# ================================================================================================
# PRE-CHUNK COMBINER
# ================================================================================================


class DescribePreChunkCombiner:
    """Unit-test suite for `unstructured.chunking.base.PreChunkCombiner`."""

    def it_combines_sequential_small_pre_chunks(self):
        opts = ChunkingOptions(max_characters=250, combine_text_under_n_chars=250)
        pre_chunks = [
            PreChunk(
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                overlap_prefix="",
                opts=opts,
            ),
            PreChunk([Table("Heading\nCell text")], overlap_prefix="", opts=opts),
            PreChunk(
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                overlap_prefix="",
                opts=opts,
            ),
            PreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                overlap_prefix="",
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Table("Heading\nCell text"),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_respects_the_specified_combination_threshold(self):
        opts = ChunkingOptions(max_characters=250, combine_text_under_n_chars=80)
        pre_chunks = [
            PreChunk(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                overlap_prefix="",
                opts=opts,
            ),
            PreChunk(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                overlap_prefix="",
                opts=opts,
            ),
            # -- len == 139
            PreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                overlap_prefix="",
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_respects_the_hard_maximum_window_length(self):
        opts = ChunkingOptions(max_characters=200, combine_text_under_n_chars=200)
        pre_chunks = [
            PreChunk(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                overlap_prefix="",
                opts=opts,
            ),
            PreChunk(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                overlap_prefix="",
                opts=opts,
            ),
            # -- len == 139
            PreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                overlap_prefix="",
                opts=opts,
            ),
            # -- len == 214
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_accommodates_and_isolates_an_oversized_pre_chunk(self):
        """Such as occurs when a single element exceeds the window size."""
        opts = ChunkingOptions(max_characters=150, combine_text_under_n_chars=150)
        pre_chunks = [
            PreChunk([Title("Lorem Ipsum")], overlap_prefix="", opts=opts),
            PreChunk(  # 179
                [
                    Text(
                        "Lorem ipsum dolor sit amet consectetur adipiscing elit."  # 55
                        " Mauris nec urna non augue vulputate consequat eget et nisi."  # 60
                        " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."  # 64
                    )
                ],
                overlap_prefix="",
                opts=opts,
            ),
            PreChunk([Title("Vulputate Consequat")], overlap_prefix="", opts=opts),
        ]

        pre_chunk_iter = PreChunkCombiner(
            pre_chunks, ChunkingOptions(max_characters=150, combine_text_under_n_chars=150)
        ).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [Title("Lorem Ipsum")]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit."
                " Mauris nec urna non augue vulputate consequat eget et nisi."
                " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."
            )
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [Title("Vulputate Consequat")]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)


class Describe_PreChunkAccumulator:
    """Unit-test suite for `unstructured.chunking.base._PreChunkAccumulator`."""

    def it_generates_a_combined_PreChunk_when_flushed_and_resets_itself_to_empty(self):
        opts = ChunkingOptions(combine_text_under_n_chars=500)
        accum = _PreChunkAccumulator(opts=opts)

        pre_chunk = PreChunk(
            [
                Title("Lorem Ipsum"),
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            ],
            overlap_prefix="elementum.",
            opts=opts,
        )
        assert accum.will_fit(pre_chunk)
        accum.add_pre_chunk(pre_chunk)

        pre_chunk = PreChunk(
            [
                Title("Mauris Nec"),
                Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            ],
            overlap_prefix="sit amet.",
            opts=opts,
        )
        assert accum.will_fit(pre_chunk)
        accum.add_pre_chunk(pre_chunk)

        pre_chunk = PreChunk(
            [
                Title("Sed Orci"),
                Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
            ],
            overlap_prefix="consequat.",
            opts=opts,
        )
        assert accum.will_fit(pre_chunk)
        accum.add_pre_chunk(pre_chunk)

        pre_chunk_iter = accum.flush()

        # -- iterator generates exactly one pre_chunk --
        pre_chunk = next(pre_chunk_iter)
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)
        # -- and it is a PreChunk containing all the elements --
        assert isinstance(pre_chunk, PreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
        ]
        # -- but only the first overlap-prefix --
        assert pre_chunk._overlap_prefix == "elementum."
        # -- and the prior flush emptied the accumulator --
        with pytest.raises(StopIteration):
            next(accum.flush())

    def but_it_does_not_generate_a_PreChunk_on_flush_when_empty(self):
        accum = _PreChunkAccumulator(opts=ChunkingOptions(max_characters=150))
        assert list(accum.flush()) == []


# ================================================================================================
# (SEMANTIC) BOUNDARY PREDICATES
# ================================================================================================


class Describe_is_on_next_page:
    """Unit-test suite for `unstructured.chunking.base.is_on_next_page()` function.

    `is_on_next_page()` is not itself a predicate, rather it returns a predicate on Element
    (`Callable[[Element], bool]`) that can be called repeatedly to detect section changes in an
    element stream.
    """

    @pytest.mark.parametrize(
        "element", [Text("abcd"), Text("efgh", metadata=ElementMetadata(page_number=4))]
    )
    def it_is_unconditionally_false_for_the_first_element(self, element: Element):
        """The first page never represents a page-break."""
        pred = is_on_next_page()
        assert not pred(element)

    def it_is_false_for_an_element_that_has_no_page_number(self):
        """An element with a `None` page-number is assumed to continue the current page."""
        pred = is_on_next_page()
        assert not pred(Text("abcd", metadata=ElementMetadata(page_number=1)))
        assert not pred(Text("efgh"))
        assert not pred(Text("ijkl"))

    def it_is_false_for_an_element_with_the_current_page_number(self):
        pred = is_on_next_page()
        assert not pred(Text("abcd", metadata=ElementMetadata(page_number=1)))
        assert not pred(Text("efgh"))
        assert not pred(Text("ijkl", metadata=ElementMetadata(page_number=1)))
        assert not pred(Text("mnop"))

    def it_assigns_page_number_1_to_a_first_element_that_has_no_page_number(self):
        pred = is_on_next_page()
        assert not pred(Text("abcd"))
        assert not pred(Text("efgh", metadata=ElementMetadata(page_number=1)))

    def it_is_true_for_an_element_with_an_explicit_different_page_number(self):
        pred = is_on_next_page()
        assert not pred(Text("abcd", metadata=ElementMetadata(page_number=1)))
        assert pred(Text("efgh", metadata=ElementMetadata(page_number=2)))

    def and_it_is_true_even_when_that_page_number_is_lower(self):
        pred = is_on_next_page()
        assert not pred(Text("abcd", metadata=ElementMetadata(page_number=4)))
        assert pred(Text("efgh", metadata=ElementMetadata(page_number=2)))
        assert not pred(Text("ijkl", metadata=ElementMetadata(page_number=2)))
        assert not pred(Text("mnop"))
        assert pred(Text("qrst", metadata=ElementMetadata(page_number=3)))


class Describe_is_title:
    """Unit-test suite for `unstructured.chunking.base.is_title()` predicate."""

    def it_is_true_for_a_Title_element(self):
        assert is_title(Title("abcd"))

    @pytest.mark.parametrize(
        "element",
        [
            PageBreak(""),
            Table("Header Col 1  Header Col 2\n" "Lorem ipsum   adipiscing"),
            Text("abcd"),
        ],
    )
    def and_it_is_false_for_any_other_element_subtype(self, element: Element):
        assert not is_title(element)
