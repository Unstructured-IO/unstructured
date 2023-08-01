# https://developers.notion.com/reference/rich-text
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin
from unstructured.ingest.connector.notion.types.date import Date
from unstructured.ingest.connector.notion.types.user import User


@dataclass
class Annotation(FromJSONMixin):
    bold: bool
    italic: bool
    strikethrough: bool
    underline: bool
    code: bool
    color: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class Equation(FromJSONMixin):
    expression: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class MentionDatabase(FromJSONMixin):
    id: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class MentionLinkPreview(FromJSONMixin):
    url: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class MentionPage(FromJSONMixin):
    id: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class MentionTemplate(FromJSONMixin):
    template_mention_date: Optional[str]
    template_mention_user: Optional[str]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class Mention(FromJSONMixin):
    type: str
    database: Optional[MentionDatabase] = None
    date: Optional[Date] = None
    link_preview: Optional[MentionLinkPreview] = None
    page: Optional[MentionPage] = None
    template_mention: Optional[MentionTemplate] = None
    user: Optional[User] = None

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        mention = cls(type=t)
        if t == "date":
            mention.date = Date.from_dict(data["date"])
        elif t == "database":
            mention.date = MentionDatabase.from_dict(data["database"])
        elif t == "link_preview":
            mention.link_preview = MentionLinkPreview.from_dict(data["link_preview"])
        elif t == "page":
            mention.page = MentionPage.from_dict(data["page"])
        elif t == "template_mention":
            mention.template_mention = MentionTemplate.from_dict(data["template_mention"])
        elif t == "user":
            mention.user = User.from_dict(data["user"])

        return mention


@dataclass
class Text(FromJSONMixin):
    content: str
    link: Optional[dict]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class RichText(FromJSONMixin):
    type: str
    plain_text: str
    annotations: List[Annotation] = field(default_factory=list)
    href: Optional[str] = None
    text: Optional[Text] = None
    mention: Optional[Mention] = None
    equation: Optional[Equation] = None

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        rich_text = cls(
            type=data["type"],
            plain_text=data["plain_text"],
            href=data.get("href"),
        )
        if t == "text":
            rich_text.text = Text.from_dict(data["text"])
        elif t == "mention":
            rich_text.mention = Mention.from_dict(data["mention"])
        elif t == "equation":
            rich_text.equation = Equation.from_dict(data["equation"])

        return rich_text


if __name__ == "__main__":
    import json

    js = """
{
  "type": "mention",
  "mention": {
    "type": "page",
    "page": {
      "id": "3c612f56-fdd0-4a30-a4d6-bda7d7426309"
    }
  },
  "annotations": {
    "bold": false,
    "italic": false,
    "strikethrough": false,
    "underline": false,
    "code": false,
    "color": "default"
  },
  "plain_text": "This is a test page",
  "href": "https://www.notion.so/3c612f56fdd04a30a4d6bda7d7426309"
}
    """
    j = json.loads(js)
    rt = RichText.from_dict(j)
    print(rt)
