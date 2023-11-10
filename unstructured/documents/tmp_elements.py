"""Temporary test-bed for prototyping and review of a dynamic ElementMetadata object.

- [ ] Do we want any special behavior on `.__eq__()` like only check known fields maybe?

- [ ] We may want to consider whether end-users should be able to add ad-hoc fields to "sub"
      metadata objects too, like `DataSourceMetadata` and conceivably `CoordinatesMetadata`
      (although I'm not immediately seeing a use-case for the second one).

- [ ] Maybe we should store `None` for an ad-hoc field when the user purposely assigns that ... so
      they can get a uniform value? That's complicated by JSON round-trip though because we'd have
      to store `null` for that in JSON ... hmm.. maybe not do this.

- [ ] We have no way to distinguish an ad-hoc field from any "noise" fields that might appear in a
      JSON/dict loaded using `.from_dict()`, so unlike the original (which only loaded
      known-fields), we'll rehydrate anything that we find there.


Key Questions:

- [ ] What is the behavior we want for "debug" fields?
    - always populate when assigned (can't really avoid that probably)
    - never include in dict/JSON form?
    - behaviors changed by a flag or environment variable of some sort?
    - what options do we want for setting these fields?:
        - debug fields are "registered" when a flag is set and so can be specified in a constructor.
        - debug fields are not registered but can be set by assignment like an end-user meta field.

- [ ] Should flag be a constant? Wouldn't it be better to be an environment variable so you didn't
      need a source-code change to set/clear it?

- [ ] How many flags are we going to want? Should we have a catch-all like DEBUG and all debugging
      fields trigger off the same one?

- [ ] Debug fields are populated unconditionally, but are discarded at construction-time when a flag
      is not set.

- No real type-safety is possible on ad-hoc fields but the type-checker does not complain because
  the type of all ad-hoc fields is `Any` (which is the best available behavior in my view).

- Current implementation of `ElementMetadata.merge()` returns `self` such that `meta.merge()` can
  conveniently be used in an assignment statement like:
  `self.metadata = common_metadata.merge(differentiated_metadata)`.

  This seems risky to me however because it hides the mutation that's happening and if
  `common_metadata` is used repeatedly then it will accumulate historical values. I'd say either
  name it to `.update()` and give it `dict.update()` semantics (including returning `None`),
  or make it produce a new ElementMetadata instance and return that.

  I went with the former for now.

"""

from __future__ import annotations

import copy
import uuid
from types import MappingProxyType
from typing import Any, Dict, FrozenSet, List, Optional

from unstructured.documents.elements import (
    UUID,
    CoordinatesMetadata,
    DataSourceMetadata,
    Link,
    NoID,
    RegexMetadata,
)
from unstructured.utils import lazyproperty


class ElementMetadata:
    """Fully-dynamic replacement for dataclass-based ElementMetadata."""

    # NOTE(scanny): To add a field:
    # - Add the field declaration with type here at the top. This makes it a "known" field and
    #   enables type-checking and completion.
    # - Add a parameter with default for field in __init__() and assign it in __init__() body.
    # - Add a consolidation strategy for the field below in `ConsolidationStrategy`
    #   `.field_consolidation_strategies()` to be used when combining elements during chunking.

    attached_to_filename: Optional[str]
    category_depth: Optional[int]
    coordinates: Optional[CoordinatesMetadata]
    data_source: Optional[DataSourceMetadata]
    detection_class_prob: Optional[float]
    emphasized_text_contents: Optional[List[str]]
    emphasized_text_tags: Optional[List[str]]
    file_directory: Optional[str]
    filename: Optional[str]
    filetype: Optional[str]
    header_footer_type: Optional[str]
    image_path: Optional[str]
    is_continuation: Optional[bool]
    languages: Optional[List[str]]
    last_modified: Optional[str]
    link_texts: Optional[List[str]]
    link_urls: Optional[List[str]]
    links: Optional[List[Link]]
    page_name: Optional[str]
    page_number: Optional[int]
    parent_id: Optional[str | uuid.UUID | NoID | UUID]
    regex_metadata: Optional[Dict[str, List[RegexMetadata]]]
    section: Optional[str]
    sent_from: Optional[List[str]]
    sent_to: Optional[List[str]]
    subject: Optional[str]
    text_as_html: Optional[str]
    url: Optional[str]

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
        filename: Optional[str] = None,
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
        self.file_directory = file_directory
        self.filename = filename
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
        return self.__dict__ == other.__dict__

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert this metadata to dict form, suitable for JSON serialization.

        The returned dict is "sparse" in that no key-value pair appears for a field with value
        `None`.
        """
        meta_dict = copy.deepcopy(dict(self._fields))
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

        """
        if not isinstance(other, ElementMetadata):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("argument to '.update()' must be an instance of 'ElementMetadata'")

        for field_name, field_value in other._fields.items():
            setattr(self, field_name, field_value)

    @property
    def _fields(self) -> MappingProxyType[str, Any]:
        """Populated metadata fields in this object as a read-only dict.

        Basically `self.__dict__` but it needs a little filtering to remove entries like
        "_known_field_names".
        """
        return MappingProxyType(
            {key: value for key, value in self.__dict__.items() if not key.startswith("_")}
        )

    @lazyproperty
    def _known_field_names(self) -> FrozenSet[str]:
        """field-names for non-user-defined fields, available on all ElementMetadata instances."""
        return frozenset(self.__annotations__)
