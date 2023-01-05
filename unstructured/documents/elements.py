from abc import ABC
import hashlib
from typing import Callable, Union


class NoID(ABC):
    """Class to indicate that an element do not have an ID."""

    pass


class Element(ABC):
    """An element is a section of a page in the document."""

    def __init__(self, element_id: Union[str, NoID] = NoID()):
        self.id: Union[str, NoID] = element_id


class Text(Element):
    """Base element for capturing free text from within document."""

    category = "Uncategorized"

    def __init__(self, text: str, element_id: Union[str, NoID] = NoID()):
        self.text: str = text

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        super().__init__(element_id=element_id)

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return self.text == other.text

    def apply(self, *cleaners: Callable):
        """Applies a cleaning brick to the text element. The function that's passed in
        should take a string as input and produce a string as output."""
        cleaned_text = self.text
        for cleaner in cleaners:
            cleaned_text = cleaner(cleaned_text)

        if not isinstance(cleaned_text, str):
            raise ValueError("Cleaner produced a non-string output.")

        self.text = cleaned_text


class NarrativeText(Text):
    """NarrativeText is an element consisting of multiple, well-formulated sentences. This
    excludes elements such titles, headers, footers, and captions."""

    category = "NarrativeText"

    pass


class ListItem(Text):
    """ListItem is a NarrativeText element that is part of a list."""

    category = "ListItem"

    pass


class Title(Text):
    """A text element for capturing titles."""

    category = "Title"

    pass


class Image(Text):
    """A text element for capturing image metadata."""

    category = "Image"

    pass
