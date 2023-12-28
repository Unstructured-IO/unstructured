from __future__ import annotations

import abc
import copy
import dataclasses as dc
import enum
import functools
import hashlib
import inspect
import os
import pathlib
import re
import uuid
from types import MappingProxyType
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple, Union, cast

from typing_extensions import ParamSpec, TypeAlias, TypedDict

from unstructured.documents.coordinates import (
    TYPE_TO_COORDINATE_SYSTEM_MAP,
    CoordinateSystem,
    RelativeCoordinateSystem,
)
from unstructured.partition.utils.constants import UNSTRUCTURED_INCLUDE_DEBUG_METADATA
from unstructured.utils import lazyproperty

Point: TypeAlias = Tuple[float, float]
Points: TypeAlias = Tuple[Point, ...]


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
    def from_dict(cls, input_dict: Dict[str, Any]):
        # Only use existing fields when constructing
        supported_fields = [f.name for f in dc.fields(cls)]
        args = {k: v for k, v in input_dict.items() if k in supported_fields}

        return cls(**args)


@dc.dataclass
class CoordinatesMetadata:
    """Metadata fields that pertain to the coordinates of the element."""

    points: Optional[Points]
    system: Optional[CoordinateSystem]

    def __init__(self, points: Optional[Points], system: Optional[CoordinateSystem]):
        # Both `points` and `system` must be present; one is not meaningful without the other.
        if (points is None and system is not None) or (points is not None and system is None):
            raise ValueError(
                "Coordinates points should not exist without coordinates system and vice versa.",
            )
        self.points = points
        self.system = system

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CoordinatesMetadata):
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
    def from_dict(cls, input_dict: Dict[str, Any]):
        # `input_dict` may contain a tuple of tuples or a list of lists
        def convert_to_points(sequence_of_sequences: Sequence[Sequence[float]]) -> Points:
            points: List[Point] = []
            for seq in sequence_of_sequences:
                if isinstance(seq, list):
                    points.append(cast(Point, tuple(seq)))
                elif isinstance(seq, tuple):
                    points.append(cast(Point, seq))
            return tuple(points)

        # -- parse points --
        input_points = input_dict.get("points")
        points = convert_to_points(input_points) if input_points is not None else None

        # -- parse system --
        system_name = input_dict.get("system")
        width = input_dict.get("layout_width")
        height = input_dict.get("layout_height")
        system = (
            None
            if system_name is None
            else RelativeCoordinateSystem()
            if system_name == "RelativeCoordinateSystem"
            else TYPE_TO_COORDINATE_SYSTEM_MAP[system_name](width, height)
            if (
                width is not None
                and height is not None
                and system_name in TYPE_TO_COORDINATE_SYSTEM_MAP
            )
            else None
        )

        return cls(points=points, system=system)


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


class ElementMetadata:
    """Fully-dynamic replacement for dataclass-based ElementMetadata."""

    # NOTE(scanny): To add a field:
    # - Add the field declaration with type here at the top. This makes it a "known" field and
    #   enables type-checking and completion.
    # - Add a parameter with default for field in __init__() and assign it in __init__() body.
    # - Add a consolidation strategy for the field below in `ConsolidationStrategy`
    #   `.field_consolidation_strategies()` to be used when consolidating metadata fields of a
    #   section's elements during chunking.
    # - Add field-name to DEBUG_FIELD_NAMES if it shouldn't appear in dict/JSON or participate in
    #   equality comparison.

    attached_to_filename: Optional[str]
    category_depth: Optional[int]
    coordinates: Optional[CoordinatesMetadata]
    data_source: Optional[DataSourceMetadata]
    # -- Detection Model Class Probabilities from Unstructured-Inference Hi-Res --
    detection_class_prob: Optional[float]
    # -- DEBUG field, the detection mechanism that emitted this element --
    detection_origin: Optional[str]
    emphasized_text_contents: Optional[List[str]]
    emphasized_text_tags: Optional[List[str]]
    file_directory: Optional[str]
    filename: Optional[str]
    filetype: Optional[str]
    image_path: Optional[str]
    image_base64: Optional[str]
    image_mime_type: Optional[str]
    # -- specific to DOCX which has distinct primary, first-page, and even-page header/footers --
    header_footer_type: Optional[str]
    # -- used in chunks only, when chunk must be split mid-text to fit window --
    is_continuation: Optional[bool]
    languages: Optional[List[str]]
    last_modified: Optional[str]
    link_texts: Optional[List[str]]
    link_urls: Optional[List[str]]
    links: Optional[List[Link]]
    # -- the worksheet name in XLXS documents --
    page_name: Optional[str]
    # -- page numbers currently supported for DOCX, HTML, PDF, and PPTX documents --
    page_number: Optional[int]
    parent_id: Optional[str | uuid.UUID | NoID | UUID]
    # -- "fields" e.g. status, dept.no, etc. extracted from text via regex --
    regex_metadata: Optional[Dict[str, List[RegexMetadata]]]
    # -- EPUB document section --
    section: Optional[str]

    # -- e-mail specific metadata fields --
    sent_from: Optional[List[str]]
    sent_to: Optional[List[str]]
    subject: Optional[str]

    # -- used for Table elements to capture rows/col structure --
    text_as_html: Optional[str]
    url: Optional[str]

    # -- debug fields can be assigned and referenced using dotted-notation but are not serialized
    # -- to dict/JSON, do not participate in equality comparison, and are not included in the
    # -- `.fields` dict used by other parts of the library like chunking and weaviate.
    DEBUG_FIELD_NAMES = frozenset(["detection_origin"])

    def __init__(
        self,
        attached_to_filename: Optional[str] = None,
        category_depth: Optional[int] = None,
        coordinates: Optional[CoordinatesMetadata] = None,
        data_source: Optional[DataSourceMetadata] = None,
        detection_class_prob: Optional[float] = None,
        emphasized_text_contents: Optional[List[str]] = None,
        emphasized_text_tags: Optional[List[str]] = None,
        file_directory: Optional[str] = None,
        filename: Optional[str | pathlib.Path] = None,
        filetype: Optional[str] = None,
        header_footer_type: Optional[str] = None,
        image_path: Optional[str] = None,
        is_continuation: Optional[bool] = None,
        languages: Optional[List[str]] = None,
        last_modified: Optional[str] = None,
        link_texts: Optional[List[str]] = None,
        link_urls: Optional[List[str]] = None,
        links: Optional[List[Link]] = None,
        page_name: Optional[str] = None,
        page_number: Optional[int] = None,
        parent_id: Optional[str | uuid.UUID | NoID | UUID] = None,
        regex_metadata: Optional[Dict[str, List[RegexMetadata]]] = None,
        section: Optional[str] = None,
        sent_from: Optional[List[str]] = None,
        sent_to: Optional[List[str]] = None,
        subject: Optional[str] = None,
        text_as_html: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        self.attached_to_filename = attached_to_filename
        self.category_depth = category_depth
        self.coordinates = coordinates
        self.data_source = data_source
        self.detection_class_prob = detection_class_prob
        self.emphasized_text_contents = emphasized_text_contents
        self.emphasized_text_tags = emphasized_text_tags

        # -- accommodate pathlib.Path for filename --
        filename = str(filename) if isinstance(filename, pathlib.Path) else filename
        # -- produces "", "" when filename arg is None --
        directory_path, file_name = os.path.split(filename or "")
        # -- prefer `file_directory` arg if specified, otherwise split of file-path passed as
        # -- `filename` arg, or None if `filename` is the empty string.
        self.file_directory = file_directory or directory_path or None
        self.filename = file_name or None

        self.filetype = filetype
        self.header_footer_type = header_footer_type
        self.image_path = image_path
        self.is_continuation = is_continuation
        self.languages = languages
        self.last_modified = last_modified
        self.link_texts = link_texts
        self.link_urls = link_urls
        self.links = links
        self.page_name = page_name
        self.page_number = page_number
        self.parent_id = parent_id
        self.regex_metadata = regex_metadata
        self.section = section
        self.sent_from = sent_from
        self.sent_to = sent_to
        self.subject = subject
        self.text_as_html = text_as_html
        self.url = url

    def __eq__(self, other: object) -> bool:
        """Implments equivalence, like meta == other_meta.

        All fields at all levels must match. Unpopulated fields are not considered except when
        populated in one and not the other.
        """
        if not isinstance(other, ElementMetadata):
            return False
        return self.fields == other.fields

    def __getattr__(self, attr_name: str) -> None:
        """Only called when attribute doesn't exist."""
        if attr_name in self._known_field_names:
            return None
        raise AttributeError(f"'ElementMetadata' object has no attribute '{attr_name}'")

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __value is None:
            # -- can't use `hasattr()` for this because it calls `__getattr__()` to find out --
            if __name in self.__dict__:
                delattr(self, __name)
            return
        if not UNSTRUCTURED_INCLUDE_DEBUG_METADATA and __name in self.DEBUG_FIELD_NAMES:
            return
        super().__setattr__(__name, __value)

    @classmethod
    def from_dict(cls, meta_dict: Dict[str, Any]) -> ElementMetadata:
        """Construct from a metadata-dict.

        This would generally be a dict formed using the `.to_dict()` method and stored as JSON
        before "rehydrating" it using this method.
        """
        # -- avoid unexpected mutation by working on a copy of provided dict --
        meta_dict = copy.deepcopy(meta_dict)
        self = ElementMetadata()
        for field_name, field_value in meta_dict.items():
            if field_name == "coordinates":
                self.coordinates = CoordinatesMetadata.from_dict(field_value)
            elif field_name == "data_source":
                self.data_source = DataSourceMetadata.from_dict(field_value)
            else:
                setattr(self, field_name, field_value)

        return self

    @property
    def fields(self) -> MappingProxyType[str, Any]:
        """Populated metadata fields in this object as a read-only dict.

        Basically `self.__dict__` but it needs a little filtering to remove entries like
        "_known_field_names". Note this is a *snapshot* and will not reflect later changes.
        """
        return MappingProxyType(
            {
                field_name: field_value
                for field_name, field_value in self.__dict__.items()
                if not field_name.startswith("_") and field_name not in self.DEBUG_FIELD_NAMES
            }
        )

    @property
    def known_fields(self) -> MappingProxyType[str, Any]:
        """Populated non-ad-hoc fields in this object as a read-only dict.

        Only fields declared at the top of this class are included. Ad-hoc fields added to this
        instance by assignment are not. Note this is a *snapshot* and will not reflect changes that
        occur after this call.
        """
        known_field_names = self._known_field_names
        return MappingProxyType(
            {
                field_name: field_value
                for field_name, field_value in self.__dict__.items()
                if (field_name in known_field_names and field_name not in self.DEBUG_FIELD_NAMES)
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert this metadata to dict form, suitable for JSON serialization.

        The returned dict is "sparse" in that no key-value pair appears for a field with value
        `None`.
        """
        meta_dict = copy.deepcopy(dict(self.fields))

        # -- remove fields that should not be serialized --
        for field_name in self.DEBUG_FIELD_NAMES:
            meta_dict.pop(field_name, None)

        # -- don't serialize empty lists --
        meta_dict: Dict[str, Any] = {
            field_name: value
            for field_name, value in meta_dict.items()
            if value != [] and value != {}
        }

        # -- serialize sub-object types when present --
        if self.coordinates is not None:
            meta_dict["coordinates"] = self.coordinates.to_dict()
        if self.data_source is not None:
            meta_dict["data_source"] = self.data_source.to_dict()

        return meta_dict

    def update(self, other: ElementMetadata) -> None:
        """Update self with all fields present in `other`.

        Semantics are like those of `dict.update()`.

        - fields present in both `self` and `other` will be updated to the value in `other`.
        - fields present in `other` but not `self` will be added to `self`.
        - fields present in `self` but not `other` are unchanged.
        - `other` is unchanged.
        - both ad-hoc and known fields participate in update with the same semantics.

        Note that fields listed in DEBUG_FIELD_NAMES are skipped in this process. Those can only be
        updated by direct assignment to the instance.
        """
        if not isinstance(other, ElementMetadata):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("argument to '.update()' must be an instance of 'ElementMetadata'")

        for field_name, field_value in other.fields.items():
            setattr(self, field_name, field_value)

    @lazyproperty
    def _known_field_names(self) -> FrozenSet[str]:
        """field-names for non-user-defined fields, available on all ElementMetadata instances.

        Note that the first call to this lazyproperty adds a `"_known_field_names"` item to the
        `__dict__` of this instance, so this be called *before* iterating through `self.__dict__`
        to avoid a mid-iteration mutation.
        """
        # -- self.__annotations__ is a dict and iterating it produces its keys, which are the
        # -- field-names we want here.
        return frozenset(self.__annotations__)


class ConsolidationStrategy(enum.Enum):
    """Methods by which a metadata field can be consolidated across a collection of elements.

    These are assigned to `ElementMetadata` field-names immediately below. Metadata consolidation is
    part of the chunking process and may arise elsewhere as well.
    """

    DROP = "drop"
    """Do not include this field in the consolidated metadata object."""

    FIRST = "first"
    """Use the first value encountered, omit if not present in any elements."""

    LIST_CONCATENATE = "LIST_CONCATENATE"
    """Concatenate the list values across elements. Only suitable for fields of `List` type."""

    LIST_UNIQUE = "list_unique"
    """Union list values across elements, preserving order. Only suitable for `List` fields."""

    REGEX = "regex"
    """Combine regex-metadata of elements, adjust start and stop offsets for concatenated text."""

    @classmethod
    def field_consolidation_strategies(cls) -> Dict[str, ConsolidationStrategy]:
        """Mapping from ElementMetadata field-name to its consolidation strategy.

        Note that only _TextSection objects ("pre-chunks" containing only `Text` elements that are
        not `Table`) have their metadata consolidated, so these strategies are only applicable for
        non-Table Text elements.
        """
        return {
            "attached_to_filename": cls.FIRST,
            "category_depth": cls.DROP,
            "coordinates": cls.DROP,
            "data_source": cls.FIRST,
            "detection_class_prob": cls.DROP,
            "detection_origin": cls.DROP,
            "emphasized_text_contents": cls.LIST_CONCATENATE,
            "emphasized_text_tags": cls.LIST_CONCATENATE,
            "file_directory": cls.FIRST,
            "filename": cls.FIRST,
            "filetype": cls.FIRST,
            "header_footer_type": cls.DROP,
            "image_path": cls.DROP,
            "image_base64": cls.DROP,
            "image_mime_type": cls.DROP,
            "is_continuation": cls.DROP,  # -- not expected, added by chunking, not before --
            "languages": cls.LIST_UNIQUE,
            "last_modified": cls.FIRST,
            "link_texts": cls.LIST_CONCATENATE,
            "link_urls": cls.LIST_CONCATENATE,
            "links": cls.DROP,  # -- deprecated field --
            "max_characters": cls.DROP,  # -- unused, remove from ElementMetadata --
            "page_name": cls.FIRST,
            "page_number": cls.FIRST,
            "parent_id": cls.DROP,
            "regex_metadata": cls.REGEX,
            "section": cls.FIRST,
            "sent_from": cls.FIRST,
            "sent_to": cls.FIRST,
            "subject": cls.FIRST,
            "text_as_html": cls.DROP,  # -- not expected, only occurs in _TableSection --
            "url": cls.FIRST,
        }


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


class ElementType:
    TITLE = "Title"
    TEXT = "Text"
    UNCATEGORIZED_TEXT = "UncategorizedText"
    NARRATIVE_TEXT = "NarrativeText"
    BULLETED_TEXT = "BulletedText"
    ABSTRACT = "Abstract"
    THREADING = "Threading"
    FORM = "Form"
    FIELD_NAME = "Field-Name"
    VALUE = "Value"
    LINK = "Link"
    COMPOSITE_ELEMENT = "CompositeElement"
    IMAGE = "Image"
    PICTURE = "Picture"
    FIGURE_CAPTION = "FigureCaption"
    FIGURE = "Figure"
    CAPTION = "Caption"
    LIST = "List"
    LIST_ITEM = "ListItem"
    LIST_ITEM_OTHER = "List-item"
    CHECKED = "Checked"
    UNCHECKED = "Unchecked"
    ADDRESS = "Address"
    EMAIL_ADDRESS = "EmailAddress"
    PAGE_BREAK = "PageBreak"
    FORMULA = "Formula"
    TABLE = "Table"
    HEADER = "Header"
    HEADLINE = "Headline"
    SUB_HEADLINE = "Subheadline"
    PAGE_HEADER = "Page-header"  # Title?
    SECTION_HEADER = "Section-header"
    FOOTER = "Footer"
    FOOTNOTE = "Footnote"
    PAGE_FOOTER = "Page-footer"

    @classmethod
    def to_dict(cls):
        """
        Convert class attributes to a dictionary.

        Returns:
            dict: A dictionary where keys are attribute names and values are attribute values.
        """
        return {
            attr: getattr(cls, attr)
            for attr in dir(cls)
            if not callable(getattr(cls, attr)) and not attr.startswith("__")
        }


class Element(abc.ABC):
    """An element is a section of a page in the document."""

    text: str

    def __init__(
        self,
        element_id: Union[str, uuid.UUID, NoID, UUID] = NoID(),
        coordinates: Optional[Tuple[Tuple[float, float], ...]] = None,
        coordinate_system: Optional[CoordinateSystem] = None,
        metadata: Optional[ElementMetadata] = None,
        detection_origin: Optional[str] = None,
    ):
        self.id: Union[str, uuid.UUID, NoID, UUID] = element_id
        self.metadata = ElementMetadata() if metadata is None else metadata
        if coordinates is not None or coordinate_system is not None:
            self.metadata.coordinates = CoordinatesMetadata(
                points=coordinates, system=coordinate_system
            )
        self.metadata.detection_origin = detection_origin
        # -- all `Element` instances get a `text` attribute, defaults to the empty string if not
        # -- defined in a subclass.
        self.text = self.text if hasattr(self, "text") else ""

    def id_to_uuid(self):
        self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": None,
            "element_id": self.id,
            "text": self.text,
            "metadata": self.metadata.to_dict(),
        }

    def convert_coordinates_to_new_system(
        self, new_system: CoordinateSystem, in_place: bool = True
    ) -> Optional[Points]:
        """Converts the element location coordinates to a new coordinate system.

        If inplace is true, changes the coordinates in place and updates the coordinate system.
        """
        if (
            self.metadata.coordinates is None
            or self.metadata.coordinates.system is None
            or self.metadata.coordinates.points is None
        ):
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
    """A checkbox with an attribute indicating whether its checked or not.

    Primarily used in documents that are forms.
    """

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CheckBox):
            return False
        return all(
            (
                self.checked == other.checked,
                self.metadata.coordinates == other.metadata.coordinates,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible (str keys) dict."""
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

    def __eq__(self, other: object):
        if not isinstance(other, Text):
            return False
        return all(
            (
                self.text == other.text,
                self.metadata.coordinates == other.metadata.coordinates,
                self.category == other.category,
                self.embeddings == other.embeddings,
            ),
        )

    def __str__(self):
        return self.text

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible (str keys) dict."""
        out = super().to_dict()
        out["element_id"] = self.id
        out["type"] = self.category
        out["text"] = self.text
        if self.embeddings:
            out["embeddings"] = self.embeddings
        return out

    def apply(self, *cleaners: Callable[[str], str]):
        """Applies a cleaning brick to the text element.

        The function that's passed in should take a string as input and produce a string as
        output.
        """
        cleaned_text = self.text
        for cleaner in cleaners:
            cleaned_text = cleaner(cleaned_text)

        if not isinstance(cleaned_text, str):  # pyright: ignore[reportUnnecessaryIsInstance]
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

    category = ElementType.IMAGE


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
    ElementType.TITLE: Title,
    ElementType.SECTION_HEADER: Title,
    ElementType.HEADLINE: Title,
    ElementType.SUB_HEADLINE: Title,
    ElementType.FIELD_NAME: Title,
    ElementType.UNCATEGORIZED_TEXT: Text,
    ElementType.COMPOSITE_ELEMENT: Text,
    ElementType.TEXT: NarrativeText,
    ElementType.NARRATIVE_TEXT: NarrativeText,
    # this mapping favors ensures yolox produces backward compatible categories
    ElementType.ABSTRACT: NarrativeText,
    ElementType.THREADING: NarrativeText,
    ElementType.FORM: NarrativeText,
    ElementType.VALUE: NarrativeText,
    ElementType.LINK: NarrativeText,
    ElementType.LIST_ITEM: ListItem,
    ElementType.BULLETED_TEXT: ListItem,
    ElementType.LIST_ITEM_OTHER: ListItem,
    ElementType.HEADER: Header,
    ElementType.PAGE_HEADER: Header,  # Title?
    ElementType.FOOTER: Footer,
    ElementType.PAGE_FOOTER: Footer,
    ElementType.FOOTNOTE: Footer,
    ElementType.FIGURE_CAPTION: FigureCaption,
    ElementType.CAPTION: FigureCaption,
    ElementType.IMAGE: Image,
    ElementType.FIGURE: Image,
    ElementType.PICTURE: Image,
    ElementType.TABLE: Table,
    ElementType.ADDRESS: Address,
    ElementType.EMAIL_ADDRESS: EmailAddress,
    ElementType.FORMULA: Formula,
    ElementType.PAGE_BREAK: PageBreak,
}
