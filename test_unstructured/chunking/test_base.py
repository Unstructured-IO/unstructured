# pyright: reportPrivateUsage=false

"""Unit-test suite for the `unstructured.chunking.base` module."""

from __future__ import annotations

from typing import List

import pytest

from unstructured.chunking.base import (
    BasePreChunker,
    ChunkingOptions,
    PreChunkBuilder,
    PreChunkCombiner,
    TablePreChunk,
    TextPreChunk,
    TextPreChunkAccumulator,
    is_in_next_section,
    is_on_next_page,
    is_title,
)
from unstructured.documents.elements import (
    CheckBox,
    CompositeElement,
    Element,
    ElementMetadata,
    PageBreak,
    RegexMetadata,
    Table,
    TableChunk,
    Text,
    Title,
)

# ================================================================================================
# CHUNKING OPTIONS
# ================================================================================================


class DescribeChunkingOptions:
    """Unit-test suite for `unstructured.chunking.base.ChunkingOptions objects."""

    @pytest.mark.parametrize("max_characters", [0, -1, -42])
    def it_rejects_max_characters_not_greater_than_zero(self, max_characters: int):
        with pytest.raises(
            ValueError,
            match=f"'max_characters' argument must be > 0, got {max_characters}",
        ):
            ChunkingOptions.new(max_characters=max_characters)

    def it_does_not_complain_when_specifying_max_characters_by_itself(self):
        """Caller can specify `max_characters` arg without specifying any others.

        In particular, When `combine_text_under_n_chars` is not specified it defaults to the value
        of `max_characters`; it has no fixed default value that can be greater than `max_characters`
        and trigger an exception.
        """
        try:
            ChunkingOptions.new(max_characters=50)
        except ValueError:
            pytest.fail("did not accept `max_characters` as option by itself")

    @pytest.mark.parametrize("n_chars", [-1, -42])
    def it_rejects_combine_text_under_n_chars_for_n_less_than_zero(self, n_chars: int):
        with pytest.raises(
            ValueError,
            match=f"'combine_text_under_n_chars' argument must be >= 0, got {n_chars}",
        ):
            ChunkingOptions.new(combine_text_under_n_chars=n_chars)

    def it_accepts_0_for_combine_text_under_n_chars_to_disable_chunk_combining(self):
        """Specifying `combine_text_under_n_chars=0` is how a caller disables chunk-combining."""
        opts = ChunkingOptions.new(combine_text_under_n_chars=0)
        assert opts.combine_text_under_n_chars == 0

    def it_does_not_complain_when_specifying_combine_text_under_n_chars_by_itself(self):
        """Caller can specify `combine_text_under_n_chars` arg without specifying other options."""
        try:
            opts = ChunkingOptions.new(combine_text_under_n_chars=50)
        except ValueError:
            pytest.fail("did not accept `combine_text_under_n_chars` as option by itself")

        assert opts.combine_text_under_n_chars == 50

    def it_silently_accepts_combine_text_under_n_chars_greater_than_maxchars(self):
        """`combine_text_under_n_chars` > `max_characters` doesn't affect chunking behavior.

        So rather than raising an exception or warning, we just cap that value at `max_characters`
        which is the behavioral equivalent.
        """
        try:
            opts = ChunkingOptions.new(max_characters=500, combine_text_under_n_chars=600)
        except ValueError:
            pytest.fail("did not accept `combine_text_under_n_chars` greater than `max_characters`")

        assert opts.combine_text_under_n_chars == 500

    @pytest.mark.parametrize("n_chars", [-1, -42])
    def it_rejects_new_after_n_chars_for_n_less_than_zero(self, n_chars: int):
        with pytest.raises(
            ValueError,
            match=f"'new_after_n_chars' argument must be >= 0, got {n_chars}",
        ):
            ChunkingOptions.new(new_after_n_chars=n_chars)

    def it_does_not_complain_when_specifying_new_after_n_chars_by_itself(self):
        """Caller can specify `new_after_n_chars` arg without specifying any other options.

        In particular, `combine_text_under_n_chars` value is adjusted down to the
        `new_after_n_chars` value when the default for `combine_text_under_n_chars` exceeds the
        value of `new_after_n_chars`.
        """
        try:
            opts = ChunkingOptions.new(new_after_n_chars=200)
        except ValueError:
            pytest.fail("did not accept `new_after_n_chars` as option by itself")

        assert opts.soft_max == 200
        assert opts.combine_text_under_n_chars == 200

    def it_accepts_0_for_new_after_n_chars_to_put_each_element_into_its_own_chunk(self):
        """Specifying `new_after_n_chars=0` places each element into its own pre-chunk.

        This puts each element into its own chunk, although long chunks are still split.
        """
        opts = ChunkingOptions.new(new_after_n_chars=0)
        assert opts.soft_max == 0

    def it_silently_accepts_new_after_n_chars_greater_than_maxchars(self):
        """`new_after_n_chars` > `max_characters` doesn't affect chunking behavior.

        So rather than raising an exception or warning, we just cap that value at `max_characters`
        which is the behavioral equivalent.
        """
        try:
            opts = ChunkingOptions.new(max_characters=444, new_after_n_chars=555)
        except ValueError:
            pytest.fail("did not accept `new_after_n_chars` greater than `max_characters`")

        assert opts.soft_max == 444

    def it_knows_the_text_separator_string(self):
        assert ChunkingOptions.new().text_separator == "\n\n"


# ================================================================================================
# BASE PRE-CHUNKER
# ================================================================================================


class DescribeBasePreChunker:
    """Unit-test suite for `unstructured.chunking.base.BasePreChunker` objects."""

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

        opts = ChunkingOptions.new(max_characters=150, new_after_n_chars=65)

        pre_chunk_iter = BasePreChunker.iter_pre_chunks(elements, opts=opts)

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet, consectetur adipiscing elit."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Text("Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Ut Enim"),
            Text("Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [Text("Ut aliquip ex ea commodo consequat."), CheckBox()]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)


# ================================================================================================
# PRE-CHUNK SUBTYPES
# ================================================================================================


class DescribeTablePreChunk:
    """Unit-test suite for `unstructured.chunking.base.TablePreChunk` objects."""

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
        text_table = "Header Col 1  Header Col 2\n" "Lorem ipsum   adipiscing"
        pre_chunk = TablePreChunk(
            Table(text_table, metadata=ElementMetadata(text_as_html=html_table)),
            opts=ChunkingOptions.new(max_characters=175),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert isinstance(chunk, Table)
        assert chunk.text == "Header Col 1  Header Col 2\nLorem ipsum   adipiscing"
        assert chunk.metadata.text_as_html == (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1 </th><th>Header Col 2 </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lorem ipsum  </td><td>adipiscing   </td></tr>\n"
            "</tbody>\n"
            "</table>"
        )
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def but_it_splits_its_table_into_TableChunks_when_the_table_text_exceeds_the_window(self):
        # fixed-overhead = 8+8+9+8+9+8 = 50
        # per-row overhead = 27
        html_table = (
            "<table>\n"  # 8
            "<thead>\n"  # 8
            "<tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>\n"
            "</thead>\n"  # 9
            "<tbody>\n"  # 8
            "<tr><td>Lorem ipsum    </td><td>A Link example</td></tr>\n"
            "<tr><td>Consectetur    </td><td>adipiscing elit</td></tr>\n"
            "<tr><td>Nunc aliquam   </td><td>id enim nec molestie</td></tr>\n"
            "<tr><td>Vivamus quis   </td><td>nunc ipsum donec ac fermentum</td></tr>\n"
            "</tbody>\n"  # 9
            "</table>"  # 8
        )
        text_table = (
            "Header Col 1   Header Col 2\n"
            "Lorem ipsum    dolor sit amet\n"
            "Consectetur    adipiscing elit\n"
            "Nunc aliquam   id enim nec molestie\n"
            "Vivamus quis   nunc ipsum donec ac fermentum"
        )
        pre_chunk = TablePreChunk(
            Table(text_table, metadata=ElementMetadata(text_as_html=html_table)),
            opts=ChunkingOptions.new(max_characters=100),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == (
            "Header Col 1   Header Col 2\n"
            "Lorem ipsum    dolor sit amet\n"
            "Consectetur    adipiscing elit\n"
            "Nunc aliqua"
        )
        assert chunk.metadata.text_as_html == (
            "<table>\n"
            "<thead>\n"
            "<tr><th>Header Col 1   </th><th>Header Col 2  </th></tr>\n"
            "</thead>\n"
            "<tbody>\n"
            "<tr><td>Lo"
        )
        # --
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert (
            chunk.text == "m   id enim nec molestie\nVivamus quis   nunc ipsum donec ac fermentum"
        )
        assert chunk.metadata.text_as_html == (
            "rem ipsum    </td><td>A Link example</td></tr>\n"
            "<tr><td>Consectetur    </td><td>adipiscing elit</td><"
        )
        # -- note that text runs out but HTML continues because it's significantly longer. So two
        # -- of these chunks have HTML but no text.
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == ""
        assert chunk.metadata.text_as_html == (
            "/tr>\n"
            "<tr><td>Nunc aliquam   </td><td>id enim nec molestie</td></tr>\n"
            "<tr><td>Vivamus quis   </td><td>"
        )
        # --
        chunk = next(chunk_iter)
        assert isinstance(chunk, TableChunk)
        assert chunk.text == ""
        assert chunk.metadata.text_as_html == (
            "nunc ipsum donec ac fermentum</td></tr>\n</tbody>\n</table>"
        )
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)


class DescribeTextPreChunk:
    """Unit-test suite for `unstructured.chunking.base.TextPreChunk` objects."""

    def it_can_combine_itself_with_another_TextPreChunk_instance(self):
        """.combine() produces a new pre-chunk by appending the elements of `other_pre-chunk`.

        Note that neither the original or other pre_chunk are mutated.
        """
        opts = ChunkingOptions.new()
        pre_chunk = TextPreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ],
            opts=opts,
        )
        other_pre_chunk = TextPreChunk(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            opts=opts,
        )

        new_pre_chunk = pre_chunk.combine(other_pre_chunk)

        assert new_pre_chunk == TextPreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            opts=opts,
        )
        assert pre_chunk == TextPreChunk(
            [
                Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                Text("In rhoncus ipsum sed lectus porta volutpat."),
            ],
            opts=opts,
        )
        assert other_pre_chunk == TextPreChunk(
            [
                Text("Donec semper facilisis metus finibus malesuada."),
                Text("Vivamus magna nibh, blandit eu dui congue, feugiat efficitur velit."),
            ],
            opts=opts,
        )

    def it_generates_a_single_chunk_from_its_elements_if_they_together_fit_in_window(self):
        pre_chunk = TextPreChunk(
            [
                Title("Introduction"),
                Text(
                    "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                    "lectus porta volutpat.",
                ),
            ],
            opts=ChunkingOptions.new(max_characters=200),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert chunk == CompositeElement(
            "Introduction\n\nLorem ipsum dolor sit amet consectetur adipiscing elit."
            " In rhoncus ipsum sedlectus porta volutpat.",
        )
        assert chunk.metadata is pre_chunk._consolidated_metadata

    def but_it_generates_split_chunks_when_its_single_element_exceeds_window_size(self):
        # -- Chunk-splitting only occurs when a *single* element is too big to fit in the window.
        # -- The pre-chunker will isolate that element in a pre_chunk of its own.
        pre_chunk = TextPreChunk(
            [
                Text(
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod"
                    " tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim"
                    " veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea"
                    " commodo consequat."
                ),
            ],
            opts=ChunkingOptions.new(max_characters=200),
        )

        chunk_iter = pre_chunk.iter_chunks()

        chunk = next(chunk_iter)
        assert chunk == CompositeElement(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod"
            " tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim"
            " veniam, quis nostrud exercitation ullamco laboris nisi ut a"
        )
        assert chunk.metadata is pre_chunk._consolidated_metadata
        # --
        chunk = next(chunk_iter)
        assert chunk == CompositeElement("liquip ex ea commodo consequat.")
        assert chunk.metadata is pre_chunk._consolidated_metadata
        # --
        with pytest.raises(StopIteration):
            next(chunk_iter)

    def it_knows_the_length_of_the_combined_text_of_its_elements_which_is_the_chunk_size(self):
        """.text_length is the size of chunk this pre-chunk will produce (before any splitting)."""
        pre_chunk = TextPreChunk(
            [PageBreak(""), Text("foo"), Text("bar")], opts=ChunkingOptions.new()
        )
        assert pre_chunk.text_length == 8

    def it_extracts_all_populated_metadata_values_from_the_elements_to_help(self):
        pre_chunk = TextPreChunk(
            [
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
            ],
            opts=ChunkingOptions.new(),
        )

        assert pre_chunk._all_metadata_values == {
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

        pre_chunk = TextPreChunk(
            [
                Title("Lorem Ipsum", metadata=metadata),
                Text("'Lorem ipsum dolor' means 'Thank you very much'.", metadata=metadata_2),
            ],
            opts=ChunkingOptions.new(),
        )

        # -- ad-hoc fields "coefficient" and "quotient" do not appear --
        assert pre_chunk._all_metadata_values == {
            "category_depth": [0, 1],
            "filename": ["foo.docx", "foo.docx"],
            "image_path": ["sprite.png"],
            "languages": [["lat"], ["lat", "eng"]],
            "parent_id": ["f87731e0"],
        }

    def it_consolidates_regex_metadata_in_a_field_specific_way(self):
        """regex_metadata of chunk is combined regex_metadatas of its elements.

        Also, the `start` and `end` offsets of each regex-match are adjusted to reflect their new
        position in the chunk after element text has been concatenated.
        """
        pre_chunk = TextPreChunk(
            [
                Title(
                    "Lorem Ipsum",
                    metadata=ElementMetadata(
                        regex_metadata={"ipsum": [RegexMetadata(text="Ipsum", start=6, end=11)]},
                    ),
                ),
                Text(
                    "Lorem ipsum dolor sit amet consectetur adipiscing elit.",
                    metadata=ElementMetadata(
                        regex_metadata={
                            "dolor": [RegexMetadata(text="dolor", start=12, end=17)],
                            "ipsum": [RegexMetadata(text="ipsum", start=6, end=11)],
                        },
                    ),
                ),
                Text(
                    "In rhoncus ipsum sed lectus porta volutpat.",
                    metadata=ElementMetadata(
                        regex_metadata={"ipsum": [RegexMetadata(text="ipsum", start=11, end=16)]},
                    ),
                ),
            ],
            opts=ChunkingOptions.new(),
        )

        regex_metadata = pre_chunk._consolidated_regex_meta

        assert regex_metadata == {
            "dolor": [RegexMetadata(text="dolor", start=25, end=30)],
            "ipsum": [
                RegexMetadata(text="Ipsum", start=6, end=11),
                RegexMetadata(text="ipsum", start=19, end=24),
                RegexMetadata(text="ipsum", start=81, end=86),
            ],
        }

    def it_forms_ElementMetadata_constructor_kwargs_by_applying_consolidation_strategies(self):
        """._meta_kwargs is used like `ElementMetadata(**self._meta_kwargs)` to construct metadata.

        Only non-None fields should appear in the dict and each field value should be the
        consolidation of the values across the pre_chunk elements.
        """
        pre_chunk = TextPreChunk(
            [
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
                        regex_metadata={"ipsum": [RegexMetadata(text="Ipsum", start=6, end=11)]},
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
                        # -- regex_metadata has its own dedicated consolidation-strategy (REGEX) --
                        regex_metadata={
                            "dolor": [RegexMetadata(text="dolor", start=12, end=17)],
                            "ipsum": [RegexMetadata(text="ipsum", start=6, end=11)],
                        },
                    ),
                ),
            ],
            opts=ChunkingOptions.new(),
        )

        meta_kwargs = pre_chunk._meta_kwargs

        assert meta_kwargs == {
            "filename": "foo.docx",
            "emphasized_text_contents": ["Lorem", "Ipsum", "Lorem", "ipsum"],
            "emphasized_text_tags": ["b", "i", "i", "b"],
            "languages": ["lat", "eng"],
            "regex_metadata": {
                "ipsum": [
                    RegexMetadata(text="Ipsum", start=6, end=11),
                    RegexMetadata(text="ipsum", start=19, end=24),
                ],
                "dolor": [RegexMetadata(text="dolor", start=25, end=30)],
            },
        }

    @pytest.mark.parametrize(
        ("elements", "expected_value"),
        [
            ([Text("foo"), Text("bar")], "foo\n\nbar"),
            ([Text("foo"), PageBreak(""), Text("bar")], "foo\n\nbar"),
            ([PageBreak(""), Text("foo"), Text("bar")], "foo\n\nbar"),
            ([Text("foo"), Text("bar"), PageBreak("")], "foo\n\nbar"),
        ],
    )
    def it_knows_the_concatenated_text_of_the_pre_chunk(
        self, elements: List[Text], expected_value: str
    ):
        """._text is the "joined" text of the pre-chunk elements.

        The text-segment contributed by each element is separated from the next by a blank line
        ("\n\n"). An element that contributes no text does not give rise to a separator.
        """
        pre_chunk = TextPreChunk(elements, opts=ChunkingOptions.new())
        assert pre_chunk._text == expected_value


# ================================================================================================
# PRE-CHUNKING ACCUMULATORS
# ================================================================================================


class DescribePreChunkBuilder:
    """Unit-test suite for `unstructured.chunking.base.PreChunkBuilder`."""

    def it_is_empty_on_construction(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=50))

        assert builder._text_length == 0
        assert builder._remaining_space == 50

    def it_accumulates_elements_added_to_it(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))

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

    @pytest.mark.parametrize("element", [Table("Heading\nCell text"), Text("abcd " * 200)])
    def it_will_fit_a_Table_or_oversized_element_when_empty(self, element: Element):
        builder = PreChunkBuilder(opts=ChunkingOptions.new())
        assert builder.will_fit(element)

    @pytest.mark.parametrize(
        ("existing_element", "next_element"),
        [
            (Text("abcd"), Table("Fruits\nMango")),
            (Text("abcd"), Text("abcd " * 200)),
            (Table("Heading\nCell text"), Table("Fruits\nMango")),
            (Table("Heading\nCell text"), Text("abcd " * 200)),
        ],
    )
    def but_not_when_it_already_contains_an_element_of_any_kind(
        self, existing_element: Element, next_element: Element
    ):
        builder = PreChunkBuilder(opts=ChunkingOptions.new())
        builder.add_element(existing_element)

        assert not builder.will_fit(next_element)

    @pytest.mark.parametrize("element", [Text("abcd"), Table("Fruits\nMango")])
    def it_will_not_fit_any_element_when_it_already_contains_a_table(self, element: Element):
        builder = PreChunkBuilder(opts=ChunkingOptions.new())
        builder.add_element(Table("Heading\nCell text"))

        assert not builder.will_fit(element)

    def it_will_not_fit_an_element_when_it_already_exceeds_the_soft_maxlen(self):
        builder = PreChunkBuilder(
            opts=ChunkingOptions.new(max_characters=100, new_after_n_chars=50)
        )
        builder.add_element(
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")  # 55-chars
        )

        assert not builder.will_fit(Text("In rhoncus ipsum."))

    def and_it_will_not_fit_an_element_when_that_would_cause_it_to_exceed_the_hard_maxlen(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=100))
        builder.add_element(
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")  # 55-chars
        )

        # -- 55 + 2 (separator) + 44 == 101 --
        assert not builder.will_fit(
            Text("In rhoncus ipsum sed lectus portos volutpat.")  # 44-chars
        )

    def but_it_will_fit_an_element_that_fits(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=100))
        builder.add_element(
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit.")  # 55-chars
        )

        # -- 55 + 2 (separator) + 43 == 100 --
        assert builder.will_fit(Text("In rhoncus ipsum sed lectus porto volutpat."))  # 43-chars

    def it_generates_a_TextPreChunk_when_flushed_and_resets_itself_to_empty(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))
        builder.add_element(Title("Introduction"))
        builder.add_element(
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        )

        pre_chunk = next(builder.flush())

        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Introduction"),
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed"
                "lectus porta volutpat.",
            ),
        ]
        assert builder._text_length == 0
        assert builder._remaining_space == 150

    def but_it_generates_a_TablePreChunk_when_it_contains_a_Table_element(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))
        builder.add_element(Table("Heading\nCell text"))

        pre_chunk = next(builder.flush())

        # -- pre-chunk builder was reset before the yield, such that the iterator does not need to
        # -- be exhausted before clearing out the old elements and a new pre-chunk can be
        # -- accumulated immediately (first `next()` call is required however, to advance to the
        # -- yield statement).
        assert builder._text_length == 0
        assert builder._remaining_space == 150
        # -- pre-chunk is a `TablePreChunk` --
        assert isinstance(pre_chunk, TablePreChunk)
        assert pre_chunk._table == Table("Heading\nCell text")

    def but_it_does_not_generate_a_TextPreChunk_on_flush_when_empty(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=150))

        pre_chunks = list(builder.flush())

        assert pre_chunks == []
        assert builder._text_length == 0
        assert builder._remaining_space == 150

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        builder = PreChunkBuilder(opts=ChunkingOptions.new(max_characters=50))
        builder.add_element(Text("abcde"))
        builder.add_element(Text("fghij"))

        # -- ._text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert builder._text_length == 12
        # -- ._remaining_space is reduced by the length (2) of the trailing separator which would
        # -- go between the current text and that of the next element if one was added.
        # -- So 50 - 12 - 2 = 36 here, not 50 - 12 = 38
        assert builder._remaining_space == 36


class DescribePreChunkCombiner:
    """Unit-test suite for `unstructured.chunking.base.PreChunkCombiner`."""

    def it_combines_sequential_small_text_pre_chunks(self):
        opts = ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=250)
        pre_chunks = [
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                opts=opts,
            ),
            TextPreChunk(
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                opts=opts,
            ),
            TextPreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def but_it_does_not_combine_table_pre_chunks(self):
        opts = ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=250)
        pre_chunks = [
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ],
                opts=opts,
            ),
            TablePreChunk(Table("Heading\nCell text"), opts=opts),
            TextPreChunk(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ],
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(
            pre_chunks, ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=250)
        ).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TablePreChunk)
        assert pre_chunk._table == Table("Heading\nCell text")
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_respects_the_specified_combination_threshold(self):
        opts = ChunkingOptions.new(max_characters=250, combine_text_under_n_chars=80)
        pre_chunks = [
            TextPreChunk(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                opts=opts,
            ),
            TextPreChunk(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                opts=opts,
            ),
            # -- len == 139
            TextPreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                opts=opts,
            ),
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_respects_the_hard_maximum_window_length(self):
        opts = ChunkingOptions.new(max_characters=200, combine_text_under_n_chars=200)
        pre_chunks = [
            TextPreChunk(  # 68
                [
                    Title("Lorem Ipsum"),  # 11
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),  # 55
                ],
                opts=opts,
            ),
            TextPreChunk(  # 71
                [
                    Title("Mauris Nec"),  # 10
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),  # 59
                ],
                opts=opts,
            ),
            # -- len == 139
            TextPreChunk(
                [
                    Title("Sed Orci"),  # 8
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),  # 63
                ],
                opts=opts,
            ),
            # -- len == 214
        ]

        pre_chunk_iter = PreChunkCombiner(pre_chunks, opts=opts).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies."),
        ]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)

    def it_accommodates_and_isolates_an_oversized_pre_chunk(self):
        """Such as occurs when a single element exceeds the window size."""
        opts = ChunkingOptions.new(max_characters=150, combine_text_under_n_chars=150)
        pre_chunks = [
            TextPreChunk([Title("Lorem Ipsum")], opts=opts),
            TextPreChunk(  # 179
                [
                    Text(
                        "Lorem ipsum dolor sit amet consectetur adipiscing elit."  # 55
                        " Mauris nec urna non augue vulputate consequat eget et nisi."  # 60
                        " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."  # 64
                    )
                ],
                opts=opts,
            ),
            TextPreChunk([Title("Vulputate Consequat")], opts=opts),
        ]

        pre_chunk_iter = PreChunkCombiner(
            pre_chunks, ChunkingOptions.new(max_characters=150, combine_text_under_n_chars=150)
        ).iter_combined_pre_chunks()

        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [Title("Lorem Ipsum")]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Text(
                "Lorem ipsum dolor sit amet consectetur adipiscing elit."
                " Mauris nec urna non augue vulputate consequat eget et nisi."
                " Sed orci quam, eleifend sit amet vehicula, elementum ultricies."
            )
        ]
        # --
        pre_chunk = next(pre_chunk_iter)
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [Title("Vulputate Consequat")]
        # --
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)


class DescribeTextPreChunkAccumulator:
    """Unit-test suite for `unstructured.chunking.base.TextPreChunkAccumulator`."""

    def it_is_empty_on_construction(self):
        accum = TextPreChunkAccumulator(opts=ChunkingOptions.new(max_characters=100))

        assert accum.text_length == 0
        assert accum.remaining_space == 100

    def it_accumulates_pre_chunks_added_to_it(self):
        opts = ChunkingOptions.new(max_characters=500)
        accum = TextPreChunkAccumulator(opts=opts)

        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ],
                opts=opts,
            )
        )
        assert accum.text_length == 68
        assert accum.remaining_space == 430

        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ],
                opts=opts,
            )
        )
        assert accum.text_length == 141
        assert accum.remaining_space == 357

    def it_generates_a_TextPreChunk_when_flushed_and_resets_itself_to_empty(self):
        opts = ChunkingOptions.new(max_characters=150)
        accum = TextPreChunkAccumulator(opts=opts)
        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Lorem Ipsum"),
                    Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
                ],
                opts=opts,
            )
        )
        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Mauris Nec"),
                    Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
                ],
                opts=opts,
            )
        )
        accum.add_pre_chunk(
            TextPreChunk(
                [
                    Title("Sed Orci"),
                    Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
                ],
                opts=opts,
            )
        )

        pre_chunk_iter = accum.flush()

        # -- iterator generates exactly one pre_chunk --
        pre_chunk = next(pre_chunk_iter)
        with pytest.raises(StopIteration):
            next(pre_chunk_iter)
        # -- and it is a _TextPreChunk containing all the elements --
        assert isinstance(pre_chunk, TextPreChunk)
        assert pre_chunk._elements == [
            Title("Lorem Ipsum"),
            Text("Lorem ipsum dolor sit amet consectetur adipiscing elit."),
            Title("Mauris Nec"),
            Text("Mauris nec urna non augue vulputate consequat eget et nisi."),
            Title("Sed Orci"),
            Text("Sed orci quam, eleifend sit amet vehicula, elementum ultricies quam."),
        ]
        assert accum.text_length == 0
        assert accum.remaining_space == 150

    def but_it_does_not_generate_a_TextPreChunk_on_flush_when_empty(self):
        accum = TextPreChunkAccumulator(opts=ChunkingOptions.new(max_characters=150))

        pre_chunks = list(accum.flush())

        assert pre_chunks == []
        assert accum.text_length == 0
        assert accum.remaining_space == 150

    def it_considers_separator_length_when_computing_text_length_and_remaining_space(self):
        opts = ChunkingOptions.new(max_characters=100)
        accum = TextPreChunkAccumulator(opts=opts)
        accum.add_pre_chunk(TextPreChunk([Text("abcde")], opts=opts))
        accum.add_pre_chunk(TextPreChunk([Text("fghij")], opts=opts))

        # -- .text_length includes a separator ("\n\n", len==2) between each text-segment,
        # -- so 5 + 2 + 5 = 12 here, not 5 + 5 = 10
        assert accum.text_length == 12
        # -- .remaining_space is reduced by the length (2) of the trailing separator which would
        # -- go between the current text and that of the next pre-chunk if one was added.
        # -- So 100 - 12 - 2 = 86 here, not 100 - 12 = 88
        assert accum.remaining_space == 86


# ================================================================================================
# (SEMANTIC) BOUNDARY PREDICATES
# ================================================================================================


class Describe_is_in_next_section:
    """Unit-test suite for `unstructured.chunking.base.is_in_next_section()` function.

    `is_in_next_section()` is not itself a predicate, rather it returns a predicate on Element
    (`Callable[[Element], bool]`) that can be called repeatedly to detect section changes in an
    element stream.
    """

    def it_is_false_for_the_first_element_when_it_has_a_non_None_section(self):
        """This is an explicit first-section; first-section does not represent a section break."""
        pred = is_in_next_section()
        assert not pred(Text("abcd", metadata=ElementMetadata(section="Introduction")))

    def and_it_is_false_for_the_first_element_when_it_has_a_None_section(self):
        """This is an anonymous first-section; still doesn't represent a section break."""
        pred = is_in_next_section()
        assert not pred(Text("abcd"))

    def it_is_false_for_None_section_elements_that_follow_an_explicit_first_section(self):
        """A `None` section element is considered to continue the prior section."""
        pred = is_in_next_section()
        assert not pred(Text("abcd", metadata=ElementMetadata(section="Introduction")))
        assert not pred(Text("efgh"))
        assert not pred(Text("ijkl"))

    def and_it_is_false_for_None_section_elements_that_follow_an_anonymous_first_section(self):
        """A `None` section element is considered to continue the prior section."""
        pred = is_in_next_section()
        assert not pred(Text("abcd"))
        assert not pred(Text("efgh"))
        assert not pred(Text("ijkl"))

    def it_is_false_for_matching_section_elements_that_follow_an_explicit_first_section(self):
        pred = is_in_next_section()
        assert not pred(Text("abcd", metadata=ElementMetadata(section="Introduction")))
        assert not pred(Text("efgh", metadata=ElementMetadata(section="Introduction")))
        assert not pred(Text("ijkl", metadata=ElementMetadata(section="Introduction")))

    def it_is_true_for_an_explicit_section_element_that_follows_an_anonymous_first_section(self):
        pred = is_in_next_section()
        assert not pred(Text("abcd"))
        assert not pred(Text("efgh"))
        assert pred(Text("ijkl", metadata=ElementMetadata(section="Introduction")))

    def and_it_is_true_for_a_different_explicit_section_that_follows_an_explicit_section(self):
        pred = is_in_next_section()
        assert not pred(Text("abcd", metadata=ElementMetadata(section="Introduction")))
        assert pred(Text("efgh", metadata=ElementMetadata(section="Summary")))

    def it_is_true_whenever_the_section_explicitly_changes_except_at_the_start(self):
        pred = is_in_next_section()
        assert not pred(Text("abcd"))
        assert pred(Text("efgh", metadata=ElementMetadata(section="Introduction")))
        assert not pred(Text("ijkl"))
        assert not pred(Text("mnop", metadata=ElementMetadata(section="Introduction")))
        assert not pred(Text("qrst"))
        assert pred(Text("uvwx", metadata=ElementMetadata(section="Summary")))
        assert not pred(Text("yzab", metadata=ElementMetadata(section="Summary")))
        assert not pred(Text("cdef"))
        assert pred(Text("ghij", metadata=ElementMetadata(section="Appendix")))


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
