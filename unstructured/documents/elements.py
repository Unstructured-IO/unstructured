from abc import ABC
import hashlib
from typing import Union


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
