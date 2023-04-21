import hashlib
import pathlib
from abc import ABC
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class NoID(ABC):
    """Class to indicate that an element do not have an ID."""

    pass


@dataclass
class ElementMetadata:
    filename: Optional[str] = None
    date: Optional[str] = None

    # Page numbers currenlty supported for PDF, HTML and PPT documents
    page_number: Optional[int] = None

    # Webpage specific metadata fields
    url: Optional[str] = None

    # E-mail specific metadata fields
    sent_from: Optional[List[str]] = None
    sent_to: Optional[List[str]] = None
    subject: Optional[str] = None

    # Text format metadata fields
    text_as_html: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.filename, pathlib.Path):
            self.filename = str(self.filename)

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value is not None}

    @classmethod
    def from_dict(cls, input_dict):
        return cls(**input_dict)


class Element(ABC):
    """An element is a section of a page in the document."""

    def __init__(
        self,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        metadata: ElementMetadata = ElementMetadata(),
    ):
        self.id: Union[str, NoID] = element_id
        self.coordinates: Optional[Tuple[Tuple[float, float], ...]] = coordinates
        self.metadata = metadata

    def to_dict(self) -> dict:
        return {
            "type": None,
            "coordinates": self.coordinates,
            "element_id": self.id,
            "metadata": self.metadata.to_dict(),
        }


class CheckBox(Element):
    """A checkbox with an attribute indicating whether its checked or not. Primarily used
    in documents that are forms"""

    def __init__(
        self,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        checked: bool = False,
        metadata: ElementMetadata = ElementMetadata(),
    ):
        self.id: Union[str, NoID] = element_id
        self.coordinates: Optional[Tuple[Tuple[float, float], ...]] = coordinates
        self.checked: bool = checked
        self.metadata = metadata

    def __eq__(self, other):
        return (self.checked == other.checked) and (self.coordinates) == (other.coordinates)

    def to_dict(self) -> dict:
        return {
            "type": "CheckBox",
            "checked": self.checked,
            "coordinates": self.coordinates,
            "element_id": self.id,
            "metadata": self.metadata.to_dict(),
        }


class Text(Element):
    """Base element for capturing free text from within document."""

    category = "UncategorizedText"

    def __init__(
        self,
        text: str,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        metadata: ElementMetadata = ElementMetadata(),
    ):
        self.text: str = text

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        super().__init__(element_id=element_id, metadata=metadata, coordinates=coordinates)

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return all(
            [
                (self.text == other.text),
                (self.coordinates == other.coordinates),
                (self.category == other.category),
            ],
        )

    def to_dict(self) -> dict:
        return {
            "element_id": self.id,
            "coordinates": self.coordinates,
            "text": self.text,
            "type": self.category,
            "metadata": self.metadata.to_dict(),
        }

    def apply(self, *cleaners: Callable):
        """Applies a cleaning brick to the text element. The function that's passed in
        should take a string as input and produce a string as output."""
        cleaned_text = self.text
        for cleaner in cleaners:
            cleaned_text = cleaner(cleaned_text)

        if not isinstance(cleaned_text, str):
            raise ValueError("Cleaner produced a non-string output.")

        self.text = cleaned_text


class FigureCaption(Text):
    """An element for capturing text associated with figure captions."""

    category = "FigureCaption"

    pass


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


class Address(Text):
    """A text element for capturing addresses."""

    category = "Address"

    pass


class Image(Text):
    """A text element for capturing image metadata."""

    category = "Image"

    pass


class PageBreak(Text):
    """An element for capturing page breaks."""

    category = "PageBreak"

    def __init__(
        self,
        text: Optional[str] = None,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[List[float]] = None,
        metadata: ElementMetadata = ElementMetadata(),
    ):
        super().__init__(text="<PAGE BREAK>")


class Table(Text):
    """An element for capturing tables."""

    category = "Table"

    pass


TYPE_TO_TEXT_ELEMENT_MAP: Dict[str, Any] = {
    "UncategorizedText": Text,
    "FigureCaption": FigureCaption,
    "Figure": FigureCaption,
    "Text": NarrativeText,
    "NarrativeText": NarrativeText,
    "ListItem": ListItem,
    "BulletedText": ListItem,
    "Title": Title,
    "Address": Address,
    "Image": Image,
    "PageBreak": PageBreak,
    "Table": Table,
}
