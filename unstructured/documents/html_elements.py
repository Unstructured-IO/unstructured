"""Document elements specific to the HTML partitioner."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from unstructured.documents.elements import (
    Address,
    ElementMetadata,
    EmailAddress,
    Link,
    ListItem,
    NarrativeText,
    Table,
    Text,
    Title,
)


class HtmlElement(Protocol):
    """Interface provided by HTML-specific elements like HTMLNarrativeText."""

    links: Sequence[Link]
    metadata: ElementMetadata

    def __init__(
        self,
        text: str,
        tag: str,
        metadata: ElementMetadata | None = None,
    ): ...


class TagsMixin:
    """Mixin that allows a class to retain tag information."""

    def __init__(
        self,
        *args: Any,
        links: Sequence[Link] = [],
        **kwargs: Any,
    ):
        self.links = links
        super().__init__(*args, **kwargs)


class HTMLText(TagsMixin, Text):
    """Text with tag information."""


class HTMLAddress(TagsMixin, Address):
    """Address with tag information."""


class HTMLEmailAddress(TagsMixin, EmailAddress):
    """EmailAddress with tag information"""


class HTMLTitle(TagsMixin, Title):
    """Title with tag information."""


class HTMLNarrativeText(TagsMixin, NarrativeText):
    """NarrativeText with tag information."""


class HTMLListItem(TagsMixin, ListItem):
    """NarrativeText with tag information."""


class HTMLTable(TagsMixin, Table):
    """NarrativeText with tag information"""
