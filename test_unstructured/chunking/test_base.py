"""Unit-test suite for the `unstructured.chunking.base` module."""

from __future__ import annotations

import pytest

from unstructured.chunking.base import ChunkingOptions


class DescribeChunkingOptions:
    """Unit-test suite for `unstructured.chunking.model.ChunkingOptions objects."""

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
