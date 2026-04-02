# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.chunking.base` module."""

from __future__ import annotations

import logging
from typing import Any, Sequence

import pytest
from lxml.html import fragment_fromstring

from unstructured.chunking.base import (
    ChunkingOptions,
    PreChunk,
    PreChunkBuilder,
    PreChunkCombiner,
    PreChunker,
    TokenCounter,
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
from unstructured.chunking.dispatch import reconstruct_table_from_chunks
from unstructured.common.html_table import HtmlCell, HtmlRow, HtmlTable
from unstructured.documents.elements import (
    CheckBox,
    CodeSnippet,
    CompositeElement,
    Element,
    ElementMetadata,
    Image,
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

    @pytest.mark.parametrize(
        ("kwargs", "expected_value"),
        [
            ({"repeat_table_headers": True}, True),
            ({"repeat_table_headers": False}, False),
            ({"repeat_table_headers": None}, True),
            ({}, True),
        ],
    )
    def it_knows_whether_to_repeat_table_headers_by_default(
        self, kwargs: dict[str, Any], expected_value: bool
    ):
        assert ChunkingOptions(**kwargs).repeat_table_headers is expected_value

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

    # -- Token-based chunking tests --

    def it_rejects_max_tokens_and_max_characters_together(self):
        with pytest.raises(
            ValueError,
            match="'max_tokens' and 'max_characters' are mutually exclusive",
        ):
            ChunkingOptions(max_tokens=100, max_characters=500)._validate()

    def it_rejects_max_tokens_without_tokenizer(self):
        with pytest.raises(
            ValueError,
            match="'tokenizer' is required when using 'max_tokens'",
        ):
            ChunkingOptions(max_tokens=100)._validate()

    @pytest.mark.parametrize("max_tokens", [0, -1, -42])
    def it_rejects_max_tokens_not_greater_than_zero(self, max_tokens: int):
        with pytest.raises(
            ValueError,
            match=f"'max_tokens' argument must be > 0, got {max_tokens}",
        ):
            ChunkingOptions(max_tokens=max_tokens, tokenizer="cl100k_base")._validate()

    def it_rejects_new_after_n_tokens_without_max_tokens(self):
        with pytest.raises(
            ValueError,
            match="'new_after_n_tokens' requires 'max_tokens' to be specified",
        ):
            ChunkingOptions(new_after_n_tokens=50)._validate()

    @pytest.mark.parametrize("n_tokens", [-1, -42])
    def it_rejects_new_after_n_tokens_for_n_less_than_zero(self, n_tokens: int):
        with pytest.raises(
            ValueError,
            match=f"'new_after_n_tokens' argument must be >= 0, got {n_tokens}",
        ):
            ChunkingOptions(
                max_tokens=100, new_after_n_tokens=n_tokens, tokenizer="cl100k_base"
            )._validate()

    def it_knows_when_token_counting_is_enabled(self):
        opts_char = ChunkingOptions(max_characters=500)
        opts_token = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        assert opts_char.use_token_counting is False
        assert opts_token.use_token_counting is True

    def it_returns_hard_max_in_tokens_when_token_counting_is_enabled(self):
        opts = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        assert opts.hard_max == 100

    def it_returns_soft_max_in_tokens_when_token_counting_is_enabled(self):
        opts = ChunkingOptions(max_tokens=100, new_after_n_tokens=80, tokenizer="cl100k_base")
        assert opts.soft_max == 80

    def it_defaults_soft_max_to_hard_max_for_token_counting(self):
        opts = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        assert opts.soft_max == 100

    def it_creates_token_counter_when_tokenizer_is_specified(self):
        opts = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        assert opts.token_counter is not None

    def it_returns_no_token_counter_when_tokenizer_is_not_specified(self):
        opts = ChunkingOptions(max_characters=500)
        assert opts.token_counter is None

    def it_measures_text_in_characters_by_default(self):
        opts = ChunkingOptions(max_characters=500)
        text = "Hello, World!"
        assert opts.measure(text) == len(text)


# ================================================================================================
# TOKEN COUNTER
# ================================================================================================


class DescribeTokenCounter:
    """Unit-test suite for `unstructured.chunking.base.TokenCounter` objects."""

    @pytest.fixture
    def _tiktoken_installed(self):
        """Skip test if tiktoken is not installed."""
        pytest.importorskip("tiktoken")

    def it_counts_tokens_using_encoding_name(self, _tiktoken_installed: None):
        counter = TokenCounter("cl100k_base")
        # -- "Hello, World!" is typically tokenized as ["Hello", ",", " World", "!"] = 4 tokens --
        count = counter.count("Hello, World!")
        assert isinstance(count, int)
        assert count > 0

    def it_counts_tokens_using_model_name(self, _tiktoken_installed: None):
        counter = TokenCounter("gpt-4")
        count = counter.count("Hello, World!")
        assert isinstance(count, int)
        assert count > 0

    def it_lazily_imports_tiktoken(self, _tiktoken_installed: None):
        counter = TokenCounter("cl100k_base")
        # -- encoder should not be initialized until count is called --
        assert "_encoder" not in counter.__dict__
        counter.count("test")
        # -- now encoder should be cached --
        assert "_encoder" in counter.__dict__


# ================================================================================================
# TEXT SPLITTER (TOKEN MODE)
# ================================================================================================


class DescribeTextSplitterTokenMode:
    """Unit-test suite for `_TextSplitter` in token-based chunking mode."""

    @pytest.fixture
    def _tiktoken_installed(self):
        """Skip test if tiktoken is not installed."""
        pytest.importorskip("tiktoken")

    def it_returns_text_unchanged_when_under_token_limit(self, _tiktoken_installed: None):
        opts = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        split = _TextSplitter(opts)

        text = "Hello, World!"
        fragment, remainder = split(text)

        assert fragment == text
        assert remainder == ""

    def it_splits_oversized_text_respecting_token_limit(self, _tiktoken_installed: None):
        opts = ChunkingOptions(max_tokens=10, tokenizer="cl100k_base")
        split = _TextSplitter(opts)

        # -- create text that exceeds 10 tokens --
        text = "The quick brown fox jumps over the lazy dog. " * 5
        fragment, remainder = split(text)

        # -- fragment should be non-empty and have fewer tokens than the limit --
        assert len(fragment) > 0
        assert len(remainder) > 0
        assert opts.measure(fragment) <= 10

    def it_prefers_separator_boundaries_when_splitting(self, _tiktoken_installed: None):
        opts = ChunkingOptions(max_tokens=15, tokenizer="cl100k_base")
        split = _TextSplitter(opts)

        # -- text with clear sentence boundaries --
        text = "First sentence here. Second sentence here. Third sentence here."
        fragment, remainder = split(text)

        # -- should split on a sentence/word boundary, not mid-word --
        assert fragment.endswith(".") or fragment[-1].isalnum()
        assert not fragment.endswith(" ")

    def it_handles_text_with_no_good_split_points(self, _tiktoken_installed: None):
        opts = ChunkingOptions(max_tokens=5, tokenizer="cl100k_base")
        split = _TextSplitter(opts)

        # -- single long word repeated --
        text = "Supercalifragilisticexpialidocious " * 10
        fragment, remainder = split(text)

        # -- should still produce a valid split --
        assert len(fragment) > 0
        assert opts.measure(fragment) <= 5

    def it_applies_token_based_overlap_not_character_based(self, _tiktoken_installed: None):
        """Overlap in token mode should be measured in tokens, not characters."""
        # -- 3 tokens of overlap --
        opts = ChunkingOptions(max_tokens=10, tokenizer="cl100k_base", overlap=3)
        split = _TextSplitter(opts)

        # -- text that will need to be split (14 tokens total) --
        text = "apple banana cherry date elderberry fig grape honeydew kiwi lemon"
        fragment, remainder = split(text)

        # -- verify exact fragment content (8 tokens, split at sentence boundary) --
        assert fragment == "apple banana cherry date elderberry fig grape"
        assert opts.measure(fragment) == 8

        # -- verify exact remainder content (overlap + remaining text) --
        # -- "fig grape" is the 3-token overlap from end of fragment --
        assert remainder == "fig grape honeydew kiwi lemon"
        # -- remainder starts with overlap words from fragment --
        assert remainder.startswith("fig grape")

    def it_computes_token_overlap_tail_correctly(self, _tiktoken_installed: None):
        """Test the _get_token_overlap_tail helper method."""
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        opts = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        splitter = _TextSplitter(opts)

        text = "The quick brown fox jumps over the lazy dog."
        # -- request 3 tokens worth of tail --
        tail = splitter._get_token_overlap_tail(text, 3)

        # -- verify exact tail content: "lazy dog." is exactly 3 tokens --
        assert tail == "lazy dog."
        assert len(enc.encode(tail)) == 3

    def it_handles_overlap_when_text_has_fewer_tokens_than_target(self, _tiktoken_installed: None):
        """When text has fewer tokens than overlap target, return all text."""
        opts = ChunkingOptions(max_tokens=100, tokenizer="cl100k_base")
        splitter = _TextSplitter(opts)

        short_text = "Hello"  # Just 1 token
        tail = splitter._get_token_overlap_tail(short_text, 5)

        # -- should return the entire text (stripped) --
        assert tail == "Hello"

    def it_produces_correct_overlapping_splits(self, _tiktoken_installed: None):
        """Verify the complete split-with-overlap behavior works correctly."""
        opts = ChunkingOptions(max_tokens=8, tokenizer="cl100k_base", overlap=2)
        split = _TextSplitter(opts)

        # -- create text that will need multiple splits (12 tokens total) --
        text = "one two three four five six seven eight nine ten eleven twelve"

        # -- first split --
        fragment1, remainder1 = split(text)

        # -- verify exact first fragment (8 tokens) --
        assert fragment1 == "one two three four five six seven eight"
        assert opts.measure(fragment1) == 8

        # -- verify exact remainder with overlap --
        # -- "seven eight" is the 2-token overlap from end of fragment1 --
        assert remainder1 == "seven eight nine ten eleven twelve"
        assert remainder1.startswith("seven eight")

        # -- second split consumes remainder completely (6 tokens, under limit) --
        fragment2, remainder2 = split(remainder1)
        assert fragment2 == "seven eight nine ten eleven twelve"
        assert remainder2 == ""


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

    def it_will_fit_when_element_has_none_as_text(self):
        builder = PreChunkBuilder(opts=ChunkingOptions())
        assert builder.will_fit(Image(None))

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
    def it_will_not_fit_another_element_when_it_already_contains_a_table(self, element: Element):
        builder = PreChunkBuilder(opts=ChunkingOptions())
        builder.add_element(Table("Heading\nCell text"))

        assert not builder.will_fit(element)

    def it_will_not_fit_a_table_when_the_pre_chunk_already_has_other_elements(self):
        builder = PreChunkBuilder(opts=ChunkingOptions(max_characters=500))
        builder.add_element(Text("Preamble."))

        assert not builder.will_fit(Table("Heading\nCell text"))

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
        # -- table pre-chunks do not inherit overlap from prior narrative text --
        assert pre_chunk._text == "In rhoncus ipsum sed lectus porta volutpat."

        builder.add_element(Text("Donec semper facilisis metus finibus."))
        pre_chunk = list(builder.flush())[0]

        assert isinstance(pre_chunk, PreChunk)
        # -- narrative after a table does not inherit the table's overlap tail --
        assert pre_chunk._text == "Donec semper facilisis metus finibus."

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

    def it_can_handle_element_with_none_as_text(self):
        pre_chunk = PreChunk(
            [Image(None), Text("hello")], overlap_prefix="", opts=ChunkingOptions()
        )
        assert pre_chunk._text == "hello"

    def it_can_chunk_elements_with_none_text_without_error(self):
        """Regression test for AttributeError when Image elements have None text."""
        pre_chunk = PreChunk(
            [Image(None), Text("hello world"), Image(None)],
            overlap_prefix="",
            opts=ChunkingOptions(),
        )

        # Should not raise AttributeError when generating chunks
        chunks = list(pre_chunk.iter_chunks())

        assert len(chunks) == 1
        assert chunks[0].text == "hello world"

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

    def it_does_not_combine_when_either_pre_chunk_contains_a_table(self):
        opts = ChunkingOptions(max_characters=500, combine_text_under_n_chars=500)
        text_pre_chunk = PreChunk([Text("hello")], overlap_prefix="", opts=opts)
        table_pre_chunk = PreChunk([Table("Heading\nCell text")], overlap_prefix="", opts=opts)

        assert text_pre_chunk.can_combine(table_pre_chunk) is False
        assert table_pre_chunk.can_combine(text_pre_chunk) is False

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

    def it_preserves_whitespace_in_CodeSnippet_elements(self):
        """CodeSnippet elements should preserve their internal whitespace including newlines.

        This is important for code blocks where formatting (indentation, line breaks) is
        semantically meaningful.
        """
        code_text = "def hello():\n    print('Hello')\n    return True"
        pre_chunk = PreChunk([CodeSnippet(code_text)], overlap_prefix="", opts=ChunkingOptions())

        # The text should preserve newlines, not collapse them to spaces
        assert "\n" in pre_chunk._text
        assert pre_chunk._text == code_text

    def it_preserves_whitespace_in_CodeSnippet_when_mixed_with_other_elements(self):
        """CodeSnippet whitespace is preserved even when mixed with regular Text elements."""
        code_text = "for i in range(10):\n    print(i)"
        pre_chunk = PreChunk(
            [
                Text("Here is some code:"),
                CodeSnippet(code_text),
                Text("That was the code."),
            ],
            overlap_prefix="",
            opts=ChunkingOptions(),
        )

        # The combined text should have the code with preserved newlines
        assert "for i in range(10):\n    print(i)" in pre_chunk._text
        # Regular text elements are still joined with blank line separators
        assert "Here is some code:\n\n" in pre_chunk._text


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

    HTML_TABLE_1 = (
        "<table>\n"
        "<tr><td>Header Col 1   </td><td>Header Col 2  </td></tr>\n"
        "<tr><td>Lorem ipsum    </td><td>A Link example</td></tr>\n"
        "<tr><td>Consectetur    </td><td>adipiscing elit</td></tr>\n"
        "<tr><td>Nunc aliquam   </td><td>id enim nec molestie</td></tr>\n"
        "</table>"
    )
    TEXT_TABLE_1 = (
        "Header Col 1   Header Col 2\n"
        "Lorem ipsum    A Link example\n"
        "Consectetur    adipiscing elit\n"
        "Nunc aliquam   id enim nec molestie"
    )
    HTML_TABLE_2 = (
        "<table>\n"
        "<tr><td>Name          </td><td>Occupation              </td></tr>\n"
        "<tr><td>Alice Johnson </td><td>Software Engineer       </td></tr>\n"
        "<tr><td>Bob Williams  </td><td>Data Scientist          </td></tr>\n"
        "<tr><td>Charlie Brown </td><td>Product Manager         </td></tr>\n"
        "</table>"
    )
    TEXT_TABLE_2 = (
        "Name           Occupation\n"
        "Alice Johnson  Software Engineer\n"
        "Bob Williams   Data Scientist\n"
        "Charlie Brown  Product Manager"
    )

    @staticmethod
    def _table_chunks(
        table_text: str,
        table_html: str,
        max_characters: int,
        *,
        repeat_table_headers: bool | None = None,
    ) -> list[Table | TableChunk]:
        kwargs: dict[str, Any] = {"max_characters": max_characters}
        if repeat_table_headers is not None:
            kwargs["repeat_table_headers"] = repeat_table_headers
        opts = ChunkingOptions(**kwargs)
        table = Table(table_text, metadata=ElementMetadata(text_as_html=table_html))
        return list(_TableChunker.iter_chunks(table, overlap_prefix="", opts=opts))

    @staticmethod
    def _row_texts(table_html: str) -> list[str]:
        html_table = HtmlTable.from_html_text(table_html)
        return [" ".join(row.iter_cell_texts()) for row in html_table.iter_rows()]

    @pytest.mark.parametrize(
        ("table_html", "expected_header_row_count"),
        [
            pytest.param(
                (
                    "<table>"
                    "<tr><td>Body A</td><td>Body B</td></tr>"
                    "<tr><td>Body C</td><td>Body D</td></tr>"
                    "</table>"
                ),
                0,
                id="no-headers",
            ),
            pytest.param(
                (
                    "<table>"
                    "<tr><th>Header A</th><th>Header B</th></tr>"
                    "<tr><td>Body A</td><td>Body B</td></tr>"
                    "</table>"
                ),
                1,
                id="single-leading-header-row",
            ),
            pytest.param(
                (
                    "<table>"
                    "<tr><th>Header A</th><th>Header B</th></tr>"
                    "<tr><th>Subheader A</th><th>Subheader B</th></tr>"
                    "<tr><td>Body A</td><td>Body B</td></tr>"
                    "</table>"
                ),
                2,
                id="multiple-leading-header-rows",
            ),
            pytest.param(
                (
                    "<table>"
                    "<thead>"
                    "<tr><td>Header A</td><td>Header B</td></tr>"
                    "<tr><td>Header C</td><td>Header D</td></tr>"
                    "</thead>"
                    "<tbody>"
                    "<tr><td>Body A</td><td>Body B</td></tr>"
                    "</tbody>"
                    "</table>"
                ),
                2,
                id="thead-rows-are-headers",
            ),
            pytest.param(
                (
                    "<table>"
                    "<tr><th>Header A</th><th>Header B</th></tr>"
                    "<tr><td>Body A</td><td>Body B</td></tr>"
                    "<tr><th>Later Th A</th><th>Later Th B</th></tr>"
                    "</table>"
                ),
                1,
                id="later-th-row-is-not-promoted",
            ),
        ],
    )
    def it_detects_contiguous_leading_header_rows(
        self, table_html: str, expected_header_row_count: int
    ):
        table_chunker = _TableChunker(
            Table("header detection fixture", metadata=ElementMetadata(text_as_html=table_html)),
            overlap_prefix="",
            opts=ChunkingOptions(max_characters=500),
        )

        assert table_chunker._leading_header_row_count == expected_header_row_count

    def and_it_keeps_the_first_chunk_unchanged_when_header_repetition_is_enabled(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )
        repeated_header_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=True,
        )
        baseline_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=False,
        )

        assert len(repeated_header_chunks) >= 2
        assert len(baseline_chunks) >= 2
        assert repeated_header_chunks[0].text == baseline_chunks[0].text
        assert (
            repeated_header_chunks[0].metadata.text_as_html
            == baseline_chunks[0].metadata.text_as_html
        )
        # -- second and later chunks should differ because only continuation chunks get repeated
        # -- headers.
        assert repeated_header_chunks[1].text != baseline_chunks[1].text
        assert (
            repeated_header_chunks[1].metadata.text_as_html
            != baseline_chunks[1].metadata.text_as_html
        )

    def and_it_prepends_detected_header_rows_to_each_non_initial_chunk(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )
        chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=True,
        )

        header_text_prefix = "Header A Header B Subhead A Subhead B "
        header_html_prefix = (
            "<table>"
            "<tr><td>Header A</td><td>Header B</td></tr>"
            "<tr><td>Subhead A</td><td>Subhead B</td></tr>"
        )
        assert len(chunks) >= 2
        for chunk in chunks[1:]:
            assert chunk.text.startswith(header_text_prefix)
            assert chunk.metadata.text_as_html.startswith(header_html_prefix)

    def and_it_reproduces_loss_of_header_semantics_on_carried_header_rows(self):
        source_table_html = (
            "<table>"
            "<thead>"
            "<tr><th scope='col'>Region</th><th scope='col'>Quarter</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Northwest Territory</td><td>Q1 FY2026</td></tr>"
            "<tr><td>Southwest Territory</td><td>Q2 FY2026</td></tr>"
            "<tr><td>Midwest Territory</td><td>Q3 FY2026</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Region Quarter\n"
            "Northwest Territory Q1 FY2026\n"
            "Southwest Territory Q2 FY2026\n"
            "Midwest Territory Q3 FY2026"
        )

        chunks = self._table_chunks(
            table_text=table_text,
            table_html=source_table_html,
            max_characters=55,
            repeat_table_headers=True,
        )

        assert len(chunks) == 3
        source_table = fragment_fromstring(source_table_html)
        assert source_table.xpath(".//thead")
        assert source_table.xpath(".//th")

        continuation_html = chunks[1].metadata.text_as_html
        assert continuation_html is not None
        continuation_table = fragment_fromstring(continuation_html)
        assert continuation_table.xpath(".//thead") == []
        assert continuation_table.xpath(".//th") == []
        assert continuation_table.xpath("./tr[1]/td/text()") == ["Region", "Quarter"]

    def and_it_records_carried_over_header_row_counts_on_split_chunks(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )
        repeated_header_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=True,
        )
        opt_out_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=False,
        )

        assert [c.metadata.num_carried_over_header_rows for c in repeated_header_chunks] == [
            0,
            2,
            2,
            2,
        ]
        assert [c.metadata.num_carried_over_header_rows for c in opt_out_chunks] == [0, 0]

    def and_it_cascades_header_carry_forward_across_three_or_more_continuation_chunks(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )
        chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=True,
        )

        header_text_prefix = "Header A Header B Subhead A Subhead B "
        continuation_body_texts = [
            chunk.text.removeprefix(header_text_prefix) for chunk in chunks[1:]
        ]

        assert len(chunks) == 4
        assert continuation_body_texts == ["Body 2 Bravo", "Body 3 Charlie", "Body 4 Delta"]

    def and_it_preserves_body_rows_without_drop_duplication_or_reordering(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )

        chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=True,
        )

        expected_header_rows = ["Header A Header B", "Subhead A Subhead B"]
        expected_body_rows = ["Body 1 Alpha", "Body 2 Bravo", "Body 3 Charlie", "Body 4 Delta"]
        observed_body_rows: list[str] = []

        assert len(chunks) == 4
        for chunk in chunks:
            row_texts = self._row_texts(chunk.metadata.text_as_html or "")
            assert row_texts[:2] == expected_header_rows
            observed_body_rows.extend(row_texts[2:])

        assert observed_body_rows == expected_body_rows

    def and_it_matches_legacy_non_repeating_behavior_when_header_repetition_is_opted_out(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )

        chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=False,
        )

        assert [(chunk.text, chunk.metadata.text_as_html) for chunk in chunks] == [
            (
                "Header A Header B Subhead A Subhead B Body 1 Alpha",
                "<table>"
                "<tr><td>Header A</td><td>Header B</td></tr>"
                "<tr><td>Subhead A</td><td>Subhead B</td></tr>"
                "<tr><td>Body 1</td><td>Alpha</td></tr>"
                "</table>",
            ),
            (
                "Body 2 Bravo Body 3 Charlie Body 4 Delta",
                "<table>"
                "<tr><td>Body 2</td><td>Bravo</td></tr>"
                "<tr><td>Body 3</td><td>Charlie</td></tr>"
                "<tr><td>Body 4</td><td>Delta</td></tr>"
                "</table>",
            ),
        ]

    def and_it_handles_exact_fit_and_near_boundary_continuation_windows(self):
        header_text = "H" * 30
        row_1 = "A" * 29
        row_2 = "B" * 29
        row_3 = "C" * 29
        table_html = (
            "<table>"
            f"<tr><th>{header_text}</th></tr>"
            f"<tr><td>{row_1}</td></tr>"
            f"<tr><td>{row_2}</td></tr>"
            f"<tr><td>{row_3}</td></tr>"
            "</table>"
        )
        table_text = "\n".join((header_text, row_1, row_2, row_3))

        exact_fit_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=60,
            repeat_table_headers=True,
        )
        near_boundary_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=59,
            repeat_table_headers=True,
        )

        header_text_prefix = f"{header_text} "
        assert len(exact_fit_chunks) == 3
        assert exact_fit_chunks[1].text == f"{header_text_prefix}{row_2}"
        assert exact_fit_chunks[2].text == f"{header_text_prefix}{row_3}"
        assert len(near_boundary_chunks) > len(exact_fit_chunks)
        assert all(len(chunk.text) <= 59 for chunk in near_boundary_chunks)
        for chunk in near_boundary_chunks[1:]:
            assert chunk.text.startswith(header_text_prefix)

    def but_it_falls_back_to_non_repeating_behavior_when_header_rows_are_pathologically_large(self):
        pathological_header = "H" * 31
        table_html = (
            "<table>"
            f"<tr><th>{pathological_header}</th></tr>"
            "<tr><td>Body chunk one text</td></tr>"
            "<tr><td>Body chunk two text</td></tr>"
            "<tr><td>Body chunk three text</td></tr>"
            "</table>"
        )
        table_text = (
            f"{pathological_header}\n"
            "Body chunk one text\n"
            "Body chunk two text\n"
            "Body chunk three text"
        )

        repeated_header_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=60,
            repeat_table_headers=True,
        )
        baseline_chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=60,
            repeat_table_headers=False,
        )

        assert len(repeated_header_chunks) >= 2
        assert [(c.text, c.metadata.text_as_html) for c in repeated_header_chunks] == [
            (c.text, c.metadata.text_as_html) for c in baseline_chunks
        ]

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
            opts=ChunkingOptions(
                max_characters=100,
                text_splitting_separators=("\n", " "),
                repeat_table_headers=False,
            ),
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

    def it_handles_table_with_none_text_without_error(self):
        """Regression test for AttributeError when Table elements have None text."""
        table = Table(None)  # Table with None text

        # Should not raise AttributeError and should produce no chunks
        chunks = list(_TableChunker.iter_chunks(table, "", ChunkingOptions()))

        assert len(chunks) == 0

    def it_handles_invalid_html_in_text_as_html_without_error(self, caplog):
        """Regression test: gracefully skip HTML-based chunking when text_as_html is not valid HTML.

        `lxml` raises `ParserError` for strings that are not valid HTML fragments (e.g. plain text
        with no tags). The chunker should log a warning and fall back to text-only chunking rather
        than raising.
        """
        table = Table(
            "Header Col 1  Header Col 2\nLorem ipsum   dolor sit amet",
            metadata=ElementMetadata(text_as_html="not valid html"),
        )

        caplog.set_level(logging.WARNING)
        # -- should not raise ParserError --
        chunks = list(_TableChunker.iter_chunks(table, "", ChunkingOptions()))

        # -- falls back to text-only: a single Table chunk with no .text_as_html --
        assert len(chunks) == 1
        chunk = chunks[0]
        assert isinstance(chunk, Table)
        assert chunk.metadata.text_as_html is None
        assert len(caplog.records) == 1
        assert caplog.records[0].message.startswith("Could not parse text_as_html")
        assert caplog.records[0].message.endswith("not valid html")

    def it_handles_html_without_table_element_in_text_as_html_without_error(self, caplog):
        """Regression test: gracefully skip HTML-based chunking when text_as_html has no <table>.

        `HtmlTable.from_html_text` raises `ValueError` when the HTML is valid but contains no
        `<table>` element. The chunker should log a warning and fall back to text-only chunking
        rather than raising.
        """
        table = Table(
            "Header Col 1  Header Col 2\nLorem ipsum   dolor sit amet",
            metadata=ElementMetadata(text_as_html="<div>no table here</div>"),
        )

        caplog.set_level(logging.WARNING)
        # -- should not raise ValueError --
        chunks = list(_TableChunker.iter_chunks(table, "", ChunkingOptions()))

        # -- falls back to text-only: a single Table chunk with no .text_as_html --
        assert len(chunks) == 1
        chunk = chunks[0]
        assert isinstance(chunk, Table)
        assert chunk.metadata.text_as_html is None
        assert len(caplog.records) == 1
        assert caplog.records[0].message.startswith("Could not parse text_as_html")
        assert "<div>no table here</div>" in caplog.records[0].message

    def it_can_reconstruct_tables_from_a_mixed_element_list(self):
        """reconstruct_table_from_chunks recovers original tables from mixed chunked output.

        Verifies both text and HTML reconstruction, with two tables and non-table elements
        interspersed.
        """
        opts = ChunkingOptions(max_characters=75, text_splitting_separators=("\n", " "))

        # -- chunk two HTML tables, each with distinct metadata --
        chunks_1 = list(
            _TableChunker.iter_chunks(
                Table(
                    self.TEXT_TABLE_1,
                    metadata=ElementMetadata(
                        text_as_html=self.HTML_TABLE_1,
                        filename="doc1.pdf",
                        page_number=1,
                    ),
                ),
                overlap_prefix="",
                opts=opts,
            )
        )
        assert len(chunks_1) >= 2

        chunks_2 = list(
            _TableChunker.iter_chunks(
                Table(
                    self.TEXT_TABLE_2,
                    metadata=ElementMetadata(
                        text_as_html=self.HTML_TABLE_2,
                        filename="doc1.pdf",
                        page_number=3,
                    ),
                ),
                overlap_prefix="",
                opts=opts,
            )
        )
        assert len(chunks_2) >= 2

        elements: list[Element] = [
            CompositeElement(text="Preamble."),
            *chunks_1,
            CompositeElement(text="Interlude."),
            *chunks_2,
            CompositeElement(text="Epilogue."),
        ]

        # -- reconstruct tables from the mixed element list --
        tables = reconstruct_table_from_chunks(elements)

        assert len(tables) == 2
        for table in tables:
            assert isinstance(table, Table)
            assert not isinstance(table, TableChunk)

        # -- reconstructed text has same words in same order as original --
        assert tables[0].text.split() == self.TEXT_TABLE_1.split()
        assert tables[1].text.split() == self.TEXT_TABLE_2.split()

        # -- reconstructed HTML has same rows and cells in same order as original --
        for table, orig_html in zip(tables, [self.HTML_TABLE_1, self.HTML_TABLE_2]):
            assert table.metadata.text_as_html is not None
            reconstructed = fragment_fromstring(table.metadata.text_as_html)
            original = fragment_fromstring(orig_html)
            # -- same number of rows --
            assert len(reconstructed.findall(".//tr")) == len(original.findall(".//tr"))
            # -- same cells in same order --
            reconstructed_cells = [
                td.text_content().strip() for td in reconstructed.iter("td", "th")
            ]
            original_cells = [td.text_content().strip() for td in original.iter("td", "th")]
            assert reconstructed_cells == original_cells

        # -- metadata is preserved from original table --
        assert tables[0].metadata.filename == "doc1.pdf"
        assert tables[0].metadata.page_number == 1
        assert tables[1].metadata.filename == "doc1.pdf"
        assert tables[1].metadata.page_number == 3

    def it_reconstructs_repeated_header_tables_without_duplication_using_chunk_metadata(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>Header A</th><th>Header B</th></tr>"
            "<tr><th>Subhead A</th><th>Subhead B</th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>Body 1</td><td>Alpha</td></tr>"
            "<tr><td>Body 2</td><td>Bravo</td></tr>"
            "<tr><td>Body 3</td><td>Charlie</td></tr>"
            "<tr><td>Body 4</td><td>Delta</td></tr>"
            "</tbody>"
            "</table>"
        )
        table_text = (
            "Header A Header B\n"
            "Subhead A Subhead B\n"
            "Body 1 Alpha\n"
            "Body 2 Bravo\n"
            "Body 3 Charlie\n"
            "Body 4 Delta"
        )

        chunks = self._table_chunks(
            table_text=table_text,
            table_html=table_html,
            max_characters=55,
            repeat_table_headers=True,
        )
        assert [c.metadata.num_carried_over_header_rows for c in chunks] == [0, 2, 2, 2]

        [table] = reconstruct_table_from_chunks(chunks)

        assert table.text.split() == table_text.split()
        assert table.metadata.text_as_html is not None
        assert self._row_texts(table.metadata.text_as_html) == [
            "Header A Header B",
            "Subhead A Subhead B",
            "Body 1 Alpha",
            "Body 2 Bravo",
            "Body 3 Charlie",
            "Body 4 Delta",
        ]

    def and_it_handles_nested_markup_in_carried_header_rows_during_reconstruction(self):
        table_html = (
            "<table>"
            "<thead>"
            "<tr><th>ID</th><th><a href='#'>Category Link</a></th></tr>"
            "</thead>"
            "<tbody>"
            "<tr><td>1</td><td>Alpha data value here</td></tr>"
            "<tr><td>2</td><td>Bravo data value here</td></tr>"
            "<tr><td>3</td><td>Charlie data value here</td></tr>"
            "<tr><td>4</td><td>Delta data value here</td></tr>"
            "<tr><td>5</td><td>Echo data value here</td></tr>"
            "</tbody>"
            "</table>"
        )
        expected_row_texts = [
            "ID Category Link",
            "1 Alpha data value here",
            "2 Bravo data value here",
            "3 Charlie data value here",
            "4 Delta data value here",
            "5 Echo data value here",
        ]
        expected_text = " ".join(expected_row_texts)

        chunks = self._table_chunks(
            table_text="placeholder",
            table_html=table_html,
            max_characters=80,
            repeat_table_headers=True,
        )
        assert len(chunks) >= 2
        assert chunks[0].metadata.num_carried_over_header_rows == 0
        assert [c.metadata.num_carried_over_header_rows for c in chunks[1:]] == [1] * (
            len(chunks) - 1
        )
        for chunk in chunks[1:]:
            assert chunk.text.startswith("ID Category Link ")

        [table] = reconstruct_table_from_chunks(chunks)

        assert table.text.split() == expected_text.split()
        assert table.metadata.text_as_html is not None
        assert self._row_texts(table.metadata.text_as_html) == expected_row_texts

    def it_treats_missing_carried_header_row_counts_as_zero_during_reconstruction(self):
        """Missing carried-header metadata defaults to no carried rows during reconstruction."""
        table_id = "table-with-missing-header-count"
        chunks: list[Element] = [
            TableChunk(
                text="Header Body 1",
                metadata=ElementMetadata(
                    table_id=table_id,
                    chunk_index=0,
                    num_carried_over_header_rows=0,
                    text_as_html="<table><tr><td>Header</td></tr><tr><td>Body 1</td></tr></table>",
                ),
            ),
            TableChunk(
                text="Header Body 2",
                metadata=ElementMetadata(
                    table_id=table_id,
                    chunk_index=1,
                    num_carried_over_header_rows=None,
                    text_as_html="<table><tr><td>Header</td></tr><tr><td>Body 2</td></tr></table>",
                ),
            ),
        ]

        [table] = reconstruct_table_from_chunks(chunks)

        assert table.text == "Header Body 1 Header Body 2"
        assert table.metadata.text_as_html is not None
        assert self._row_texts(table.metadata.text_as_html) == [
            "Header",
            "Body 1",
            "Header",
            "Body 2",
        ]

    def it_orders_chunks_with_missing_chunk_index_after_numbered_chunks(self):
        """Chunks missing `chunk_index` are merged after indexed chunks for stable ordering."""
        table_id = "table-with-missing-index"
        elements: list[Element] = [
            TableChunk(
                text="third",
                metadata=ElementMetadata(
                    table_id=table_id,
                    chunk_index=None,
                    text_as_html="<table><tr><td>third</td></tr></table>",
                ),
            ),
            TableChunk(
                text="second",
                metadata=ElementMetadata(
                    table_id=table_id,
                    chunk_index=1,
                    text_as_html="<table><tr><td>second</td></tr></table>",
                ),
            ),
            TableChunk(
                text="first",
                metadata=ElementMetadata(
                    table_id=table_id,
                    chunk_index=0,
                    text_as_html="<table><tr><td>first</td></tr></table>",
                ),
            ),
        ]

        table = reconstruct_table_from_chunks(elements)[0]
        assert table.text == "first second third"

        reconstructed = fragment_fromstring(table.metadata.text_as_html)
        assert [cell.text_content().strip() for cell in reconstructed.iter("td")] == [
            "first",
            "second",
            "third",
        ]

    def it_sets_chunk_sequencing_metadata_on_table_chunks(self):
        """Split table chunks carry table_id and chunk_index for reconstruction."""
        opts = ChunkingOptions(max_characters=75, text_splitting_separators=("\n", " "))

        chunks = list(
            _TableChunker.iter_chunks(
                Table(
                    self.TEXT_TABLE_1,
                    metadata=ElementMetadata(text_as_html=self.HTML_TABLE_1),
                ),
                overlap_prefix="",
                opts=opts,
            )
        )

        assert len(chunks) >= 2
        # -- all chunks share the same table_id --
        table_ids = {c.metadata.table_id for c in chunks}
        assert len(table_ids) == 1
        assert None not in table_ids
        # -- chunk_index is sequential starting from 0 --
        assert [c.metadata.chunk_index for c in chunks] == list(range(len(chunks)))
        assert [c.metadata.num_carried_over_header_rows for c in chunks] == [0] * len(chunks)

    def it_does_not_set_chunk_sequencing_metadata_on_unsplit_table(self):
        """A table that fits in one chunk has no table_id or chunk_index."""
        chunks = list(
            _TableChunker.iter_chunks(
                Table("short", metadata=ElementMetadata(text_as_html="<table>short</table>")),
                overlap_prefix="",
                opts=ChunkingOptions(max_characters=500),
            )
        )

        assert len(chunks) == 1
        assert isinstance(chunks[0], Table)
        assert chunks[0].metadata.table_id is None
        assert chunks[0].metadata.chunk_index is None

    def it_preserves_nested_table_structure_when_reconstructing_html(self):
        """Only top-level rows should be merged; nested table rows must stay nested."""
        nested_html = "<table><tr><td><table><tr><td>Nested</td></tr></table></td></tr></table>"

        chunks: list[Element] = [
            TableChunk(
                "Nested",
                metadata=ElementMetadata(
                    text_as_html=nested_html,
                    table_id="nested-table",
                    chunk_index=0,
                ),
            )
        ]

        [table] = reconstruct_table_from_chunks(chunks)

        assert table.metadata.text_as_html is not None
        reconstructed = fragment_fromstring(table.metadata.text_as_html)
        assert len(reconstructed.xpath("./tr")) == 1
        assert len(reconstructed.xpath("./tr/td/table/tr")) == 1
        assert reconstructed.xpath("string(./tr/td/table/tr/td)").strip() == "Nested"


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
                "<table><tr><td>Maple Leafs</td><td>TOR</td><td>13</td></tr></table>",
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

    def and_it_uses_the_configured_measurement_units_for_row_fitting(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        opts = ChunkingOptions(max_characters=3)
        monkeypatch.setattr(opts, "measure", lambda text: len(text.split()))
        html_table = HtmlTable.from_html_text(
            """
            <table>
              <tr><td>supercalifragilisticexpialidocious</td></tr>
              <tr><td>pneumonoultramicroscopicsilicovolcanoconiosis</td></tr>
            </table>
            """
        )

        assert list(_HtmlTableSplitter.iter_subtables(html_table, opts)) == [
            (
                "supercalifragilisticexpialidocious pneumonoultramicroscopicsilicovolcanoconiosis",
                "<table>"
                "<tr><td>supercalifragilisticexpialidocious</td></tr>"
                "<tr><td>pneumonoultramicroscopicsilicovolcanoconiosis</td></tr>"
                "</table>",
            ),
        ]


class Describe_TextSplitter:
    """Unit-test suite for `unstructured.chunking.base._TextSplitter` objects."""

    def it_splits_on_a_preferred_separator_when_it_can(self):
        opts = ChunkingOptions(max_characters=50, text_splitting_separators=("\n", " "), overlap=10)
        split = _TextSplitter(opts)
        text = (
            "Lorem ipsum dolor amet consectetur adipiscing.  \n  In rhoncus ipsum sed lectus porta."
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
        assert accum._row_text_len == 0

    def it_accumulates_rows_added_to_it(self):
        accum = _RowAccumulator(maxlen=100)
        row = HtmlRow(fragment_fromstring("<tr><td>foo</td><td>bar</td></tr>"))

        accum.add_row(row)

        assert accum._rows == [row]
        assert accum._row_text_len == len("foo bar")

    def and_it_uses_the_configured_measurement_units_for_remaining_space(self):
        accum = _RowAccumulator(maxlen=3, measure=lambda text: len(text.split()))
        row = HtmlRow(fragment_fromstring("<tr><td>supercalifragilisticexpialidocious</td></tr>"))

        assert accum.will_fit(row) is True
        accum.add_row(row)

        # -- one token of text plus one separator leaves one token of space --
        assert accum._remaining_space == 1
        assert accum._row_text_len == 1

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
        assert accum._row_text_len == 0

    def and_the_HTML_contains_as_many_rows_as_were_accumulated(self):
        accum = _RowAccumulator(maxlen=100)
        accum.add_row(HtmlRow(fragment_fromstring("<tr><td>abcde fghij klmno</td></tr>")))
        accum.add_row(HtmlRow(fragment_fromstring("<tr><td>pqrst uvwxy z</td></tr>")))

        text, html = next(accum.flush())

        assert text == "abcde fghij klmno pqrst uvwxy z"
        assert html == (
            "<table><tr><td>abcde fghij klmno</td></tr><tr><td>pqrst uvwxy z</td></tr></table>"
        )
        assert accum._rows == []
        assert accum._row_text_len == 0

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
        ]
        pre_chunk = next(pre_chunk_iter)
        assert pre_chunk._elements == [Table("Heading\nCell text")]
        pre_chunk = next(pre_chunk_iter)
        assert pre_chunk._elements == [
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
            Table("Header Col 1  Header Col 2\nLorem ipsum   adipiscing"),
            Text("abcd"),
        ],
    )
    def and_it_is_false_for_any_other_element_subtype(self, element: Element):
        assert not is_title(element)
