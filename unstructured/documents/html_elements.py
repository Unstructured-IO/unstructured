"""Document elements specific to the HTML partitioner."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, Sequence

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

    emphasized_texts: Sequence[Dict[str, str]]
    links: Sequence[Link]
    metadata: ElementMetadata
    tag: str
    text_as_html: str | None

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
        tag: Optional[str] = None,
        links: Sequence[Link] = [],
        emphasized_texts: Sequence[Dict[str, str]] = [],
        text_as_html: Optional[str] = None,
        **kwargs: Any,
    ):
        if tag is None:
            raise TypeError("tag argument must be passed and not None")
        else:
            self.tag = tag
        self.links = links
        self.emphasized_texts = emphasized_texts
        self.text_as_html = text_as_html
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
