# https://developers.notion.com/reference/rich-text
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin, GetTextMixin
from unstructured.ingest.connector.notion.types.date import Date
from unstructured.ingest.connector.notion.types.user import People


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
class Equation(FromJSONMixin, GetTextMixin):
    expression: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.expression if self.expression else None


@dataclass
class MentionDatabase(FromJSONMixin, GetTextMixin):
    id: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.id if self.id else None


@dataclass
class MentionLinkPreview(FromJSONMixin, GetTextMixin):
    url: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.url if self.url else None


@dataclass
class MentionPage(FromJSONMixin, GetTextMixin):
    id: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.id if self.id else None


@dataclass
class MentionTemplate(FromJSONMixin):
    template_mention_date: Optional[str]
    template_mention_user: Optional[str]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class Mention(FromJSONMixin, GetTextMixin):
    type: str
    database: Optional[MentionDatabase] = None
    date: Optional[Date] = None
    link_preview: Optional[MentionLinkPreview] = None
    page: Optional[MentionPage] = None
    template_mention: Optional[MentionTemplate] = None
    user: Optional[People] = None

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        mention = cls(type=t)
        if t == "date":
            mention.date = Date.from_dict(data["date"])
        elif t == "database":
            mention.database = MentionDatabase.from_dict(data["database"])
        elif t == "link_preview":
            mention.link_preview = MentionLinkPreview.from_dict(data["link_preview"])
        elif t == "page":
            mention.page = MentionPage.from_dict(data["page"])
        elif t == "template_mention":
            mention.template_mention = MentionTemplate.from_dict(data["template_mention"])
        elif t == "user":
            mention.user = People.from_dict(data["user"])

        return mention

    def get_text(self) -> Optional[str]:
        t = self.type
        if t == "date":
            return self.date.get_text() if self.date else None
        elif t == "database":
            return self.database.get_text() if self.database else None
        elif t == "link_preview":
            return self.link_preview.get_text() if self.link_preview else None
        elif t == "page":
            return self.page.get_text() if self.page else None
        elif t == "user":
            return self.user.get_text() if self.user else None
        return None


@dataclass
class Text(FromJSONMixin):
    content: str
    link: Optional[dict]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class RichText(FromJSONMixin, GetTextMixin):
    type: str
    plain_text: str
    annotations: List[Annotation] = field(default_factory=list)
    href: Optional[str] = None
    text: Optional[Text] = None
    mention: Optional[Mention] = None
    equation: Optional[Equation] = None

    def get_text(self) -> Optional[str]:
        text = self.plain_text
        if self.href:
            text = f"[{text}]({self.href})"
        return text

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
