# https://developers.notion.com/reference/block#callout
from dataclasses import dataclass, field
from typing import List, Optional, Union

from htmlBuilder.attributes import Href, Style
from htmlBuilder.tags import A, Div, HtmlTag, P

from unstructured.ingest.connector.notion.interfaces import (
    BlockBase,
    FromJSONMixin,
    GetHTMLMixin,
)
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class EmojiIcon(FromJSONMixin, GetHTMLMixin):
    emoji: str
    type: str = "emoji"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        return P([], self.emoji)


@dataclass
class ExternalIconContent(FromJSONMixin):
    url: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class ExternalIcon(FromJSONMixin, GetHTMLMixin):
    external: ExternalIconContent
    type: str = "external"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(external=ExternalIconContent.from_dict(data=data.pop("external")), **data)

    def get_html(self) -> Optional[HtmlTag]:
        if self.external:
            return A([Href(self.external.url)], [self.external.url])
        else:
            return None


class Icon(FromJSONMixin):
    @classmethod
    def from_dict(cls, data: dict) -> Union[EmojiIcon, ExternalIcon]:
        t = data.get("type")
        if t == "emoji":
            return EmojiIcon.from_dict(data)
        elif t == "external":
            return ExternalIcon.from_dict(data)
        else:
            raise ValueError(f"Unexpected icon type: {t} ({data})")


@dataclass
class Callout(BlockBase):
    color: str
    icon: Optional[Union[EmojiIcon, ExternalIcon]] = None
    rich_text: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        return cls(
            color=data["color"],
            icon=Icon.from_dict(data.pop("icon")),
            rich_text=[RichText.from_dict(rt) for rt in rich_text],
        )

    def get_html(self) -> Optional[HtmlTag]:
        elements = []
        if self.icon and self.icon.get_html():
            elements.append(self.icon.get_html())
        if self.rich_text:
            elements.extend([rt.get_html() for rt in self.rich_text])
        attributes = []
        if self.color:
            attributes.append(Style(f"color:{self.color}"))
        return Div(attributes, elements)
