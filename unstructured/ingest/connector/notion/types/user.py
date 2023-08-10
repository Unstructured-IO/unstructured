# https://developers.notion.com/reference/user
from dataclasses import dataclass, field
from typing import Optional

from htmlBuilder.attributes import Href
from htmlBuilder.tags import A, Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin, GetHTMLMixin


@dataclass
class PartialUser(FromJSONMixin):
    id: str
    object: str = "user"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(id=data["id"])


@dataclass
class User(FromJSONMixin, GetHTMLMixin):
    object: dict
    id: str
    type: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        text = self.name
        if self.avatar_url:
            text = f"[{text}]({self.avatar_url}"
        return text

    def get_html(self) -> Optional[HtmlTag]:
        if self.avatar_url:
            return A([Href(self.avatar_url)], self.name)
        else:
            return Div([], self.name)


@dataclass
class People(User):
    person: dict = field(default_factory=dict)


@dataclass
class Bots(FromJSONMixin, GetHTMLMixin):
    object: dict
    id: str
    bot: dict
    owner: dict
    type: str
    workspace_name: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        text = self.name
        if self.avatar_url:
            text = f"[{text}]({self.avatar_url}"
        return text

    def get_html(self) -> Optional[HtmlTag]:
        if self.avatar_url:
            return A([Href(self.avatar_url)], self.name)
        else:
            return Div([], self.name)
