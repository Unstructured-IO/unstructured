from __future__ import annotations

import datetime
import hashlib
import inspect
import os
import pathlib
import re
from abc import ABC
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, Union, cast

from unstructured.documents.coordinates import CoordinateSystem


class NoID(ABC):
    """Class to indicate that an element do not have an ID."""

    pass


@dataclass
class DataSourceMetadata:
    """Metadata fields that pertain to the data source of the document."""

    url: Optional[str] = None
    version: Optional[str] = None
    record_locator: Optional[Dict[str, Any]] = None  # Values must be JSON-serializable
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    date_processed: Optional[str] = None

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value is not None}


class RegexMetadata(TypedDict):
    """Metadata that is extracted from a document element via regex."""

    text: str
    start: int
    end: int


@dataclass
class ElementMetadata:
    data_source: Optional[DataSourceMetadata] = None
    filename: Optional[str] = None
    file_directory: Optional[str] = None
    date: Optional[str] = None
    filetype: Optional[str] = None
    attached_to_filename: Optional[str] = None

    # Page numbers currenlty supported for PDF, HTML and PPT documents
    page_number: Optional[int] = None

    # Page name. The sheet name in XLXS documents.
    page_name: Optional[str] = None

    # Webpage specific metadata fields
    url: Optional[str] = None

    # E-mail specific metadata fields
    sent_from: Optional[List[str]] = None
    sent_to: Optional[List[str]] = None
    subject: Optional[str] = None

    # MSFT Word specific metadata fields
    header_footer_type: Optional[str] = None

    # Text format metadata fields
    text_as_html: Optional[str] = None

    # Metadata extracted via regex
    regex_metadata: Optional[Dict[str, List[RegexMetadata]]] = None

    def __post_init__(self):
        if isinstance(self.filename, pathlib.Path):
            self.filename = str(self.filename)

        if self.filename is not None:
            file_directory, filename = os.path.split(self.filename)
            self.file_directory = file_directory or None
            self.filename = filename

    def to_dict(self):
        _dict = {key: value for key, value in self.__dict__.items() if value is not None}
        if "regex_metadata" in _dict and not _dict["regex_metadata"]:
            _dict.pop("regex_metadata")
        if self.data_source:
            _dict["data_source"] = cast(DataSourceMetadata, self.data_source).to_dict()
        return _dict

    @classmethod
    def from_dict(cls, input_dict):
        return cls(**input_dict)

    def merge(self, other: ElementMetadata):
        for k in self.__dict__:
            if getattr(self, k) is None:
                setattr(self, k, getattr(other, k))
        return self

    def get_date(self) -> Optional[datetime.datetime]:
        """Converts the date field to a datetime object."""
        dt = None
        if self.date is not None:
            dt = datetime.datetime.fromisoformat(self.date)
        return dt


def process_metadata():
    """Decorator for processing metadata for document elements."""

    def decorator(func: Callable):
        if func.__doc__:
            if (
                "metadata_filename" in func.__code__.co_varnames
                and "metadata_filename" not in func.__doc__
            ):
                func.__doc__ += (
                    "\nMetadata Parameters:\n\tmetadata_filename:"
                    + "\n\t\tThe filename to use in element metadata."
                )
            if (
                "include_metadata" in func.__code__.co_varnames
                and "include_metadata" not in func.__doc__
            ):
                func.__doc__ += (
                    "\n\tinclude_metadata:"
                    + """\n\t\tDetermines whether or not metadata is included in the metadata
                    attribute on the elements in the output."""
                )

        @wraps(func)
        def wrapper(*args, **kwargs):
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default

            regex_metadata: Dict["str", "str"] = params.get("regex_metadata", {})
            elements = _add_regex_metadata(elements, regex_metadata)

            return elements

        return wrapper

    return decorator


def _add_regex_metadata(
    elements: List[Element],
    regex_metadata: Dict[str, str] = {},
) -> List[Element]:
    """Adds metadata based on a user provided regular expression.
    The additional metadata will be added to the regex_metadata
    attrbuted in the element metadata."""
    for element in elements:
        if isinstance(element, Text):
            _regex_metadata: Dict["str", List[RegexMetadata]] = {}
            for field_name, pattern in regex_metadata.items():
                results: List[RegexMetadata] = []
                for result in re.finditer(pattern, element.text):
                    start, end = result.span()
                    results.append(
                        {
                            "text": element.text[start:end],
                            "start": start,
                            "end": end,
                        },
                    )
                if len(results) > 0:
                    _regex_metadata[field_name] = results

            element.metadata.regex_metadata = _regex_metadata

    return elements


class Element(ABC):
    """An element is a section of a page in the document."""

    def __init__(
        self,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        metadata: Optional[ElementMetadata] = None,
    ):
        metadata = metadata if metadata else ElementMetadata()
        self.id: Union[str, NoID] = element_id
        self.coordinates: Optional[Tuple[Tuple[float, float], ...]] = coordinates
        self._coordinate_system = coordinate_system
        self.metadata = metadata

    def to_dict(self) -> dict:
        return {
            "type": None,
            "coordinates": self.coordinates,
            "coordinate_system": None
            if self._coordinate_system is None
            else str(self._coordinate_system.__class__.__name__),
            "layout_width": None
            if self._coordinate_system is None
            else self._coordinate_system.width,
            "layout_height": None
            if self._coordinate_system is None
            else self._coordinate_system.height,
            "element_id": self.id,
            "metadata": self.metadata.to_dict(),
        }

    def convert_coordinates_to_new_system(
        self,
        new_system: CoordinateSystem,
        in_place=True,
    ) -> Optional[Tuple[Tuple[Union[int, float], Union[int, float]], ...]]:
        """Converts the element location coordinates to a new coordinate system. If inplace is true,
        changes the coordinates in place and updates the coordinate system."""
        if self._coordinate_system is None or self.coordinates is None:
            return None
        new_coordinates = tuple(
            self._coordinate_system.convert_coordinates_to_new_system(
                new_system=new_system,
                x=x,
                y=y,
            )
            for x, y in self.coordinates
        )
        if in_place:
            self.coordinates = new_coordinates
            self._coordinate_system = new_system
        return new_coordinates

    @property
    def coordinate_system(self) -> Optional[Dict[str, Optional[Union[str, int, float]]]]:
        if self._coordinate_system is None:
            return None
        return {
            "name": self._coordinate_system.__class__.__name__,
            "description": self._coordinate_system.__doc__,
            "layout_width": self._coordinate_system.width,
            "layout_height": self._coordinate_system.height,
        }


class CheckBox(Element):
    """A checkbox with an attribute indicating whether its checked or not. Primarily used
    in documents that are forms"""

    def __init__(
        self,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        checked: bool = False,
        metadata: Optional[ElementMetadata] = None,
    ):
        metadata = metadata if metadata else ElementMetadata()
        super().__init__(
            element_id=element_id,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            metadata=metadata,
        )
        self.checked: bool = checked

    def __eq__(self, other):
        return (self.checked == other.checked) and (self.coordinates) == (other.coordinates)

    def to_dict(self) -> dict:
        out = super().to_dict()
        out["type"] = "CheckBox"
        out["checked"] = self.checked
        out["element_id"] = self.id
        return out


class Text(Element):
    """Base element for capturing free text from within document."""

    category = "UncategorizedText"

    def __init__(
        self,
        text: str,
        element_id: Union[str, NoID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        metadata: Optional[ElementMetadata] = None,
    ):
        metadata = metadata if metadata else ElementMetadata()
        self.text: str = text

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        super().__init__(
            element_id=element_id,
            metadata=metadata,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
        )

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return all(
            [
                (self.text == other.text),
                (self.coordinates == other.coordinates),
                (self._coordinate_system == other._coordinate_system),
                (self.category == other.category),
            ],
        )

    def to_dict(self) -> dict:
        out = super().to_dict()
        out["element_id"] = self.id
        out["type"] = self.category
        out["text"] = self.text
        return out

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


class Table(Text):
    """An element for capturing tables."""

    category = "Table"

    pass


class Header(Text):
    """An element for capturing document headers."""

    category = "Header"

    pass


class Footer(Text):
    """An element for capturing document footers."""

    category = "Footer"

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
    "Header": Header,
    "Footer": Footer,
}
