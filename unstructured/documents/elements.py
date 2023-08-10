from __future__ import annotations

import datetime
import hashlib
import inspect
import os
import pathlib
import re
import uuid
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict, Union, cast

from unstructured.documents.coordinates import (
    TYPE_TO_COORDINATE_SYSTEM_MAP,
    CoordinateSystem,
    RelativeCoordinateSystem,
)


class NoID(ABC):
    """Class to indicate that an element do not have an ID."""

    pass


class UUID(ABC):
    """Class to indicate that an element should have a UUID."""

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


@dataclass
class CoordinatesMetadata:
    """Metadata fields that pertain to the coordinates of the element."""

    points: Tuple[Tuple[float, float], ...]
    system: CoordinateSystem

    def __init__(self, points, system):
        # Both `points` and `system` must be present; one is not meaningful without the other.
        if (points is None and system is not None) or (points is not None and system is None):
            raise ValueError(
                "Coordinates points should not exist without coordinates system and vice versa.",
            )
        self.points = points
        self.system = system

    def __eq__(self, other):
        if other is None:
            return False
        return all(
            [
                (self.points == other.points),
                (self.system == other.system),
            ],
        )

    def to_dict(self):
        return {
            "points": self.points,
            "system": None if self.system is None else str(self.system.__class__.__name__),
            "layout_width": None if self.system is None else self.system.width,
            "layout_height": None if self.system is None else self.system.height,
        }

    @classmethod
    def from_dict(cls, input_dict):
        # `input_dict` may contain a tuple of tuples or a list of lists
        def convert_to_tuple_of_tuples(sequence_of_sequences):
            subsequences = []
            for seq in sequence_of_sequences:
                if isinstance(seq, list):
                    subsequences.append(tuple(seq))
                elif isinstance(seq, tuple):
                    subsequences.append(seq)
            return tuple(subsequences)

        input_points = input_dict.get("points", None)
        points = convert_to_tuple_of_tuples(input_points) if input_points is not None else None
        width = input_dict.get("layout_width", None)
        height = input_dict.get("layout_height", None)
        system = None
        if input_dict.get("system", None) == "RelativeCoordinateSystem":
            system = RelativeCoordinateSystem()
        elif (
            width is not None
            and height is not None
            and input_dict.get("system", None) in TYPE_TO_COORDINATE_SYSTEM_MAP
        ):
            system = TYPE_TO_COORDINATE_SYSTEM_MAP[input_dict["system"]](width, height)
        constructor_args = {"points": points, "system": system}
        return cls(**constructor_args)


class RegexMetadata(TypedDict):
    """Metadata that is extracted from a document element via regex."""

    text: str
    start: int
    end: int


class Link(TypedDict):
    """Metadata related to extracted links"""

    text: Optional[str]
    url: str


@dataclass
class ElementMetadata:
    coordinates: Optional[CoordinatesMetadata] = None
    data_source: Optional[DataSourceMetadata] = None
    filename: Optional[str] = None
    file_directory: Optional[str] = None
    last_modified: Optional[str] = None
    filetype: Optional[str] = None
    attached_to_filename: Optional[str] = None

    # Page numbers currenlty supported for PDF, HTML and PPT documents
    page_number: Optional[int] = None

    # Page name. The sheet name in XLXS documents.
    page_name: Optional[str] = None

    # Webpage specific metadata fields
    url: Optional[str] = None
    links: Optional[List[Link]] = None

    # E-mail specific metadata fields
    sent_from: Optional[List[str]] = None
    sent_to: Optional[List[str]] = None
    subject: Optional[str] = None

    # MSFT Word specific metadata fields
    header_footer_type: Optional[str] = None

    # Formatting metadata fields
    emphasized_texts: Optional[List[dict]] = None

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
        if self.coordinates:
            _dict["coordinates"] = cast(CoordinatesMetadata, self.coordinates).to_dict()
        return _dict

    @classmethod
    def from_dict(cls, input_dict):
        constructor_args = deepcopy(input_dict)
        if constructor_args.get("coordinates", None) is not None:
            constructor_args["coordinates"] = CoordinatesMetadata.from_dict(
                constructor_args["coordinates"],
            )
        return cls(**constructor_args)

    def merge(self, other: ElementMetadata):
        for k in self.__dict__:
            if getattr(self, k) is None:
                setattr(self, k, getattr(other, k))
        return self

    def get_last_modified(self) -> Optional[datetime.datetime]:
        """Converts the date field to a datetime object."""
        dt = None
        if self.last_modified is not None:
            dt = datetime.datetime.fromisoformat(self.last_modified)
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
        element_id: Union[str, uuid.UUID, NoID, UUID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        metadata: Optional[ElementMetadata] = None,
    ):
        if metadata is None:
            metadata = ElementMetadata()
        self.id: Union[str, uuid.UUID, NoID, UUID] = element_id
        coordinates_metadata = (
            None
            if coordinates is None and coordinate_system is None
            else (
                CoordinatesMetadata(
                    points=coordinates,
                    system=coordinate_system,
                )
            )
        )
        self.metadata = metadata.merge(ElementMetadata(coordinates=coordinates_metadata))

    def to_dict(self) -> dict:
        return {
            "type": None,
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
        if self.metadata.coordinates is None:
            return None
        new_coordinates = tuple(
            self.metadata.coordinates.system.convert_coordinates_to_new_system(
                new_system=new_system,
                x=x,
                y=y,
            )
            for x, y in self.metadata.coordinates.points
        )
        if in_place:
            self.metadata.coordinates.points = new_coordinates
            self.metadata.coordinates.system = new_system
        return new_coordinates


class CheckBox(Element):
    """A checkbox with an attribute indicating whether its checked or not. Primarily used
    in documents that are forms"""

    def __init__(
        self,
        element_id: Union[str, uuid.UUID, NoID, UUID] = NoID(),
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
        return (self.checked == other.checked) and (
            self.metadata.coordinates == other.metadata.coordinates
        )

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
        element_id: Union[str, uuid.UUID, NoID, UUID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        metadata: Optional[ElementMetadata] = None,
    ):
        metadata = metadata if metadata else ElementMetadata()
        self.text: str = text

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        elif isinstance(element_id, UUID):
            element_id = uuid.uuid4()

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
                (self.metadata.coordinates == other.metadata.coordinates),
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


class EmailAddress(Text):
    """A text element for capturing addresses"""

    category = "EmailAddress"
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
    "EmailAddress": EmailAddress,
    "Image": Image,
    "PageBreak": PageBreak,
    "Table": Table,
    "Header": Header,
    "Footer": Footer,
}
