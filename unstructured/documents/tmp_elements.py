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
from typing import Any, Dict, FrozenSet, List

from unstructured.documents.elements import CoordinatesMetadata, DataSourceMetadata
from unstructured.utils import lazyproperty


class ElementMetadata:
    """Fully-dynamic replacement for dataclass-based ElementMetadata."""

    category_depth: int | None
    coordinates: CoordinatesMetadata | None = None
    data_source: DataSourceMetadata | None
    file_directory: str | None
    languages: List[str] | None
    page_number: int | None
    text_as_html: str | None
    url: str | None

    def __init__(
        self,
        category_depth: int | None = None,
        coordinates: CoordinatesMetadata | None = None,
        data_source: DataSourceMetadata | None = None,
        file_directory: str | None = None,
        languages: List[str] | None = None,
        page_number: int | None = None,
        text_as_html: str | None = None,
        url: str | None = None,
    ) -> None:
        self.category_depth = category_depth
        self.data_source = data_source
        self.coordinates = coordinates
        self.file_directory = file_directory
        self.languages = languages
        self.page_number = page_number
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
        if attr_name in self._known_fields:
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
        return copy.deepcopy(self.__dict__)

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

        for field_name, field_value in other.__dict__.items():
            setattr(self, field_name, field_value)

    @lazyproperty
    def _known_fields(self) -> FrozenSet[str]:
        """field-names for non-user-defined fields, available on all ElementMetadata instances."""
        return frozenset(self.__annotations__)
