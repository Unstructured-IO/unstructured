from __future__ import annotations

import abc
import copy
import dataclasses as dc
import datetime
import functools
import hashlib
import inspect
import os
import pathlib
import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

from typing_extensions import ParamSpec, Self, TypedDict

from unstructured.documents.coordinates import (
    TYPE_TO_COORDINATE_SYSTEM_MAP,
    CoordinateSystem,
    RelativeCoordinateSystem,
)
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA


class NoID(abc.ABC):
    """Class to indicate that an element do not have an ID."""


class UUID(abc.ABC):
    """Class to indicate that an element should have a UUID."""


@dc.dataclass
class DataSourceMetadata:
    """Metadata fields that pertain to the data source of the document."""

    url: Optional[str] = None
    version: Optional[str] = None
    record_locator: Optional[Dict[str, Any]] = None  # Values must be JSON-serializable
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    date_processed: Optional[str] = None
    permissions_data: Optional[List[Dict[str, Any]]] = None

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value is not None}

    @classmethod
    def from_dict(cls, input_dict):
        # Only use existing fields when constructing
        supported_fields = [f.name for f in dc.fields(cls)]
        args = {k: v for k, v in input_dict.items() if k in supported_fields}

        return cls(**args)


@dc.dataclass
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
    start_index: int


@dc.dataclass
class ElementMetadata:
    coordinates: Optional[CoordinatesMetadata] = None
    data_source: Optional[DataSourceMetadata] = None
    filename: Optional[str] = None
    file_directory: Optional[str] = None
    last_modified: Optional[str] = None
    filetype: Optional[str] = None
    attached_to_filename: Optional[str] = None
    parent_id: Optional[Union[str, uuid.UUID, NoID, UUID]] = None
    category_depth: Optional[int] = None
    image_path: Optional[str] = None

    # Languages in element. TODO(newelh) - More strongly type languages
    languages: Optional[List[str]] = None

    # Page numbers currenlty supported for PDF, HTML and PPT documents
    page_number: Optional[int] = None

    # Page name. The sheet name in XLXS documents.
    page_name: Optional[str] = None

    # Webpage specific metadata fields
    url: Optional[str] = None
    link_urls: Optional[List[str]] = None
    link_texts: Optional[List[str]] = None
    links: Optional[List[Link]] = None

    # E-mail specific metadata fields
    sent_from: Optional[List[str]] = None
    sent_to: Optional[List[str]] = None
    subject: Optional[str] = None

    # Document section fields
    section: Optional[str] = None

    # MSFT Word specific metadata fields
    header_footer_type: Optional[str] = None

    # Formatting metadata fields
    emphasized_text_contents: Optional[List[str]] = None
    emphasized_text_tags: Optional[List[str]] = None

    # Text format metadata fields
    text_as_html: Optional[str] = None

    # Metadata extracted via regex
    regex_metadata: Optional[Dict[str, List[RegexMetadata]]] = None

    # Chunking metadata fields
    max_characters: Optional[int] = None
    is_continuation: Optional[bool] = None

    # Detection Model Class Probabilities from Unstructured-Inference Hi-Res
    detection_class_prob: Optional[float] = None

    if UNSTRUCTURED_INCLUDE_DEBUG_METADATA:
        # -- The detection mechanism that emitted this element, for debugging purposes. Only
        # -- defined when UNSTRUCTURED_INCLUDE_DEBUG_METADATA flag is True. Note the `compare=False`
        # -- setting meaning it's value is not included when comparing two ElementMetadata instances
        # -- for equality (`.__eq__()`).
        detection_origin: Optional[str] = dc.field(default=None, compare=False)

    def __setattr__(self, key: str, value: Any):
        # -- Avoid triggering `AttributeError` when assigning to `metadata.detection_origin` when
        # -- when the UNSTRUCTURED_INCLUDE_DEBUG_METADATA flag is False (and the `.detection_origin`
        # -- field is not defined).
        if not UNSTRUCTURED_INCLUDE_DEBUG_METADATA and key == "detection_origin":
            return
        else:
            super().__setattr__(key, value)

    def __post_init__(self):
        if isinstance(self.filename, pathlib.Path):
            self.filename = str(self.filename)

        if self.filename is not None:
            file_directory, filename = os.path.split(self.filename)
            # -- Only replace file-directory when we have something better. When ElementMetadata is
            # -- being re-loaded from JSON, the file-directory we want will already be there and
            # -- filename will be just the file-name portion of the path.
            if file_directory:
                self.file_directory = file_directory
            self.filename = filename

    def to_dict(self):
        _dict = {
            key: value
            for key, value in self.__dict__.items()
            if value is not None and key != "detection_origin"
        }
        if "regex_metadata" in _dict and not _dict["regex_metadata"]:
            _dict.pop("regex_metadata")
        if self.data_source:
            _dict["data_source"] = cast(DataSourceMetadata, self.data_source).to_dict()
        if self.coordinates:
            _dict["coordinates"] = cast(CoordinatesMetadata, self.coordinates).to_dict()
        return _dict

    @classmethod
    def from_dict(cls, input_dict: Dict[str, Any]) -> Self:
        constructor_args = copy.deepcopy(input_dict)
        if constructor_args.get("coordinates", None) is not None:
            constructor_args["coordinates"] = CoordinatesMetadata.from_dict(
                constructor_args["coordinates"],
            )
        if constructor_args.get("data_source", None) is not None:
            constructor_args["data_source"] = DataSourceMetadata.from_dict(
                constructor_args["data_source"],
            )

        # Only use existing fields when constructing
        supported_fields = [f.name for f in dc.fields(cls)]
        args = {k: v for k, v in constructor_args.items() if k in supported_fields}

        return cls(**args)

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


_P = ParamSpec("_P")


def process_metadata() -> Callable[[Callable[_P, List[Element]]], Callable[_P, List[Element]]]:
    """Post-process element-metadata for this document.

    This decorator adds a post-processing step to a document partitioner. It adds documentation for
    `metadata_filename` and `include_metadata` parameters if not present. Also adds regex-metadata
    when `regex_metadata` keyword-argument is provided and changes the element-id to a UUID when
    `unique_element_ids` argument is provided and True.
    """

    def decorator(func: Callable[_P, List[Element]]) -> Callable[_P, List[Element]]:
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

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> List[Element]:
            elements = func(*args, **kwargs)
            sig = inspect.signature(func)
            params: Dict[str, Any] = dict(**dict(zip(sig.parameters, args)), **kwargs)
            for param in sig.parameters.values():
                if param.name not in params and param.default is not param.empty:
                    params[param.name] = param.default

            regex_metadata: Dict["str", "str"] = params.get("regex_metadata", {})
            # -- don't write an empty `{}` to metadata.regex_metadata when no regex-metadata was
            # -- requested, otherwise it will serialize (because it's not None) when it has no
            # -- meaning or is even misleading. Also it complicates tests that don't use regex-meta.
            if regex_metadata:
                elements = _add_regex_metadata(elements, regex_metadata)
            unique_element_ids: bool = params.get("unique_element_ids", False)
            if unique_element_ids:
                for element in elements:
                    element.id_to_uuid()

            return elements

        return wrapper

    return decorator


def _add_regex_metadata(
    elements: List[Element],
    regex_metadata: Dict[str, str] = {},
) -> List[Element]:
    """Adds metadata based on a user provided regular expression.

    The additional metadata will be added to the regex_metadata attrbuted in the element metadata.
    """
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


class Element(abc.ABC):
    """An element is a section of a page in the document."""

    def __init__(
        self,
        element_id: Union[str, uuid.UUID, NoID, UUID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        metadata: Optional[ElementMetadata] = None,
        detection_origin: Optional[str] = None,
    ):
        if metadata is None:
            metadata = ElementMetadata()
            metadata.detection_origin = detection_origin
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
        self.metadata = metadata.merge(
            ElementMetadata(coordinates=coordinates_metadata),
        )
        self.metadata.detection_origin = detection_origin

    def id_to_uuid(self):
        self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
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
        detection_origin: Optional[str] = None,
    ):
        metadata = metadata if metadata else ElementMetadata()
        super().__init__(
            element_id=element_id,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            metadata=metadata,
            detection_origin=detection_origin,
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
        detection_origin: Optional[str] = None,
        embeddings: Optional[List[float]] = None,
    ):
        metadata = metadata if metadata else ElementMetadata()
        self.text: str = text
        self.embeddings: Optional[List[float]] = embeddings

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        elif isinstance(element_id, UUID):
            element_id = str(uuid.uuid4())

        super().__init__(
            element_id=element_id,
            metadata=metadata,
            coordinates=coordinates,
            coordinate_system=coordinate_system,
            detection_origin=detection_origin,
        )

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return all(
            [
                (self.text == other.text),
                (self.metadata.coordinates == other.metadata.coordinates),
                (self.category == other.category),
                (self.embeddings == other.embeddings),
            ],
        )

    def to_dict(self) -> dict:
        out = super().to_dict()
        out["element_id"] = self.id
        out["type"] = self.category
        out["text"] = self.text
        if self.embeddings:
            out["embeddings"] = self.embeddings
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


class Formula(Text):
    "An element containing formulas in a document"

    category = "Formula"


class CompositeElement(Text):
    """A section of text consisting of a combination of elements."""

    category = "CompositeElement"


class FigureCaption(Text):
    """An element for capturing text associated with figure captions."""

    category = "FigureCaption"


class NarrativeText(Text):
    """NarrativeText is an element consisting of multiple, well-formulated sentences. This
    excludes elements such titles, headers, footers, and captions."""

    category = "NarrativeText"


class ListItem(Text):
    """ListItem is a NarrativeText element that is part of a list."""

    category = "ListItem"


class Title(Text):
    """A text element for capturing titles."""

    category = "Title"


class Address(Text):
    """A text element for capturing addresses."""

    category = "Address"


class EmailAddress(Text):
    """A text element for capturing addresses"""

    category = "EmailAddress"


class Image(Text):
    """A text element for capturing image metadata."""

    category = "Image"


class PageBreak(Text):
    """An element for capturing page breaks."""

    category = "PageBreak"


class Table(Text):
    """An element for capturing tables."""

    category = "Table"


class TableChunk(Table):
    """An element for capturing chunks of tables."""

    category = "Table"


class Header(Text):
    """An element for capturing document headers."""

    category = "Header"


class Footer(Text):
    """An element for capturing document footers."""

    category = "Footer"


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
    "Caption": FigureCaption,
    "Footnote": Footer,
    "Formula": Formula,
    "List-item": ListItem,
    "Page-footer": Footer,
    "Page-header": Header,  # Title?
    "Picture": Image,
    # this mapping favors ensures yolox produces backward compatible categories
    "Section-header": Title,
    "Headline": Title,
    "Subheadline": Title,
    "Abstract": NarrativeText,
    "Threading": NarrativeText,
    "Form": NarrativeText,
    "Field-Name": Title,
    "Value": NarrativeText,
    "Link": NarrativeText,
}
