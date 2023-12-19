"""Chunking objects not specific to a particular chunking strategy."""

from __future__ import annotations

from typing import Optional

from typing_extensions import Self

from unstructured.utils import lazyproperty


class ChunkingOptions:
    """Specifies parameters of optional chunking behaviors."""

    def __init__(
        self,
        combine_text_under_n_chars: Optional[int] = None,
        max_characters: int = 500,
        multipage_sections: bool = True,
        new_after_n_chars: Optional[int] = None,
        overlap: int = 0,
    ):
        self._combine_text_under_n_chars_arg = combine_text_under_n_chars
        self._max_characters = max_characters
        self._multipage_sections = multipage_sections
        self._new_after_n_chars_arg = new_after_n_chars
        self._overlap = overlap

    @classmethod
    def new(
        cls,
        combine_text_under_n_chars: Optional[int] = None,
        max_characters: int = 500,
        multipage_sections: bool = True,
        new_after_n_chars: Optional[int] = None,
        overlap: int = 0,
    ) -> Self:
        """Construct validated instance.

        Raises `ValueError` on invalid arguments like overlap > max_chars.
        """
        self = cls(
            combine_text_under_n_chars,
            max_characters,
            multipage_sections,
            new_after_n_chars,
            overlap,
        )
        self._validate()
        return self

    @lazyproperty
    def combine_text_under_n_chars(self) -> int:
        """Combine consecutive text pre-chunks if former is smaller than this and both will fit.

        - Does not combine table chunks with text chunks even if they would both fit in the
          chunking window.
        - Does not combine text chunks if together they would exceed the chunking window.
        - Defaults to `max_characters` when not specified.
        - Is reduced to `new_after_n_chars` when it exceeds that value.
        """
        max_characters = self._max_characters
        soft_max = self.soft_max
        arg = self._combine_text_under_n_chars_arg

        # -- `combine_text_under_n_chars` defaults to `max_characters` when not specified and is
        # -- capped at max-chars
        combine_text_under_n_chars = max_characters if arg is None or arg > max_characters else arg

        # -- `new_after_n_chars` takes precendence on conflict with `combine_text_under_n_chars` --
        return soft_max if combine_text_under_n_chars > soft_max else combine_text_under_n_chars

    @lazyproperty
    def hard_max(self) -> int:
        """The maximum size for a chunk.

        A pre-chunk will only exceed this size when it contains exactly one element which by itself
        exceeds this size. Such a pre-chunk is subject to mid-text splitting later in the chunking
        process.
        """
        return self._max_characters

    @lazyproperty
    def multipage_sections(self) -> bool:
        """When False, break pre-chunks on page-boundaries."""
        return self._multipage_sections

    @lazyproperty
    def overlap(self) -> int:
        """The number of characters to overlap text when splitting chunks mid-text.

        The actual overlap will not exceed this number of characters but may be less as required to
        respect splitting-character boundaries.
        """
        return self._overlap

    @lazyproperty
    def soft_max(self) -> int:
        """A pre-chunk of this size or greater is considered full.

        ??? Is a value of 0 valid? It would produce the behavior: "put each element into its own
        chunk".
        """
        max_chars = self._max_characters
        new_after_n_chars = self._new_after_n_chars_arg
        return (
            max_chars
            if (new_after_n_chars is None or new_after_n_chars < 0 or new_after_n_chars > max_chars)
            else new_after_n_chars
        )

    @lazyproperty
    def text_separator(self) -> str:
        """The string to insert between elements when concatenating their text for a chunk.

        Right now this is just "\n\n" (a blank line in plain text), but having this here rather
        than as a module-level constant provides a way for us to easily make it user-configurable
        in future if we want to.
        """
        return "\n\n"

    def _validate(self) -> None:
        """Raise ValueError if requestion option-set is invalid."""
        max_characters = self._max_characters
        # -- chunking window must have positive length --
        if max_characters <= 0:
            raise ValueError(f"'max_characters' argument must be > 0," f" got {max_characters}")

        # -- `combine_text_under_n_chars == 0` is valid (suppresses chunk combination)
        # -- but a negative value is not
        combine_text_under_n_chars = self._combine_text_under_n_chars_arg
        if combine_text_under_n_chars is not None and combine_text_under_n_chars < 0:
            raise ValueError(
                f"'combine_text_under_n_chars' argument must be >= 0,"
                f" got {combine_text_under_n_chars}"
            )

        # -- a negative value for `new_after_n_chars` is assumed to
        # -- be a mistake the caller will want to know about
        new_after_n_chars = self._new_after_n_chars_arg
        if new_after_n_chars is not None and new_after_n_chars < 0:
            raise ValueError(
                f"'new_after_n_chars' argument must be >= 0," f" got {new_after_n_chars}"
            )

        # -- overlap must be less than max-chars or the chunk text will
        # -- never be consumed
        # TODO: consider a heuristic like never overlap more than half,
        # otherwise there could be corner cases leading to an infinite
        # loop (I think).
        if self._overlap >= max_characters:
            raise ValueError(f"'overlap' must be less than max_characters," f" got {self._overlap}")
