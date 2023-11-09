"""Temporary test-bed for prototyping and review of a dynamic ElementMetadata object.

- [ ] .from_dict()
- [ ] .merge()

merge creates a new ElementMetadata object where self is updated by _all populated fields_ in
`other`. So you can give precedence both ways by switching the order, like:

    self.metadata = self.metadata.merge(other_metadata)
      OR
    self.metadata = other_metadata.merge(self.metadata)

The latter of these two is the current behavior and it mutates the instance `.merge()` is called on.
It might be better named `update_empty_fields_from(other_metadata)` which is a little bit of a
complicated and non-standard behavior. I'd be thinking a behavior like that of dict.update().


Key Questions:

1. Require registration of user-defined fields?
  OR
2. Risk typos in an assignment making it into production?

- [ ] What is the behavior we want for "debug" fields?
    - always populate when assigned (can't really avoid that probably)
    - never include in dict/JSON form?
    - behaviors changed by a flag or environment variable of some sort?
    - what options do we want for setting these fields?:
        - debug fields are "registered" when a flag is set and so can be specified in a constructor.
        - debug fields are not registered but can be set by assignment like an end-user meta field.

- [ ] What about JSON-ification of things like dates? Do we want to add some custom serializers for
      common types other than (str, bool, number)?

- [ ] Should flag be a constant? Wouldn't it be better to be an environment variable so you didn't
      need a source-code change to set/clear it?

- [ ] How many flags are we going to want? Should we have a catch-all like DEBUG and all debugging
      fields trigger off the same one?

- [ ] Debug fields are populated unconditionally, but are discarded at construction-time when a flag
      is not set.

"""

from __future__ import annotations

import copy
from typing import Any, Dict, FrozenSet

from unstructured.utils import lazyproperty


class ElementMetadata:
    """Fully-dynamic replacement for dataclass-based ElementMetadata."""

    category_depth: int | None
    file_directory: str | None
    page_number: int | None
    text_as_html: str | None
    url: str | None

    def __init__(
        self,
        category_depth: int | None = None,
        file_directory: str | None = None,
        page_number: int | None = None,
        text_as_html: str | None = None,
        url: str | None = None,
    ) -> None:
        self.category_depth = category_depth
        self.file_directory = file_directory
        self.page_number = page_number
        self.text_as_html = text_as_html
        self.url = url

    def __getattr__(self, attr_name: str) -> None:
        """Only called when attribute doesn't exist."""
        if attr_name in self._known_fields:
            return None
        raise AttributeError(f"'ElementMetadata' object has no attribute '{attr_name}'")

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __value is None:
            print(f"attr {__name} was assigned None")
            # -- can't use `hasattr()` for this because it calls `__getattr__()` to find out --
            if __name in self.__dict__:
                delattr(self, __name)
            return
        super().__setattr__(__name, __value)

    # ===== WIP ====================================================

    def merge(self, other: ElementMetadata) -> ElementMetadata:
        """Update empty fields in this from `other`.

        Mutates `self` but returns `self` for convenience.
        """
        for field_name, this_value in self.__dict__.items():
            if this_value is None:
                setattr(self, field_name, getattr(other, field_name))
        return self

    # ==============================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert this metadata to dict form, suitable for JSON serialization.

        The returned dict is "sparse" in that no key-value pair appears for a field with value
        `None`.
        """
        return copy.deepcopy(self.__dict__)

    @lazyproperty
    def _known_fields(self) -> FrozenSet[str]:
        """field-names for non-user-defined fields, available on all ElementMetadata instances."""
        return frozenset(self.__annotations__)
