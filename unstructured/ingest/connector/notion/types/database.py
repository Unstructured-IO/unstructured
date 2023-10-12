# https://developers.notion.com/reference/database
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from htmlBuilder.tags import Div, HtmlTag, Span

from unstructured.ingest.connector.notion.interfaces import (
    DBPropertyBase,
    FromJSONMixin,
    GetHTMLMixin,
)
from unstructured.ingest.connector.notion.types.database_properties import (
    map_properties,
)
from unstructured.ingest.connector.notion.types.file import FileObject
from unstructured.ingest.connector.notion.types.parent import Parent
from unstructured.ingest.connector.notion.types.rich_text import RichText
from unstructured.ingest.connector.notion.types.user import PartialUser


@dataclass
class Database(FromJSONMixin, GetHTMLMixin):
    id: str
    created_time: str
    created_by: PartialUser
    last_edited_time: str
    last_edited_by: PartialUser
    archived: bool
    parent: Parent
    url: str
    is_inline: bool
    public_url: str
    request_id: Optional[str] = None
    properties: Dict[str, DBPropertyBase] = field(default_factory=dict)
    title: List[RichText] = field(default_factory=list)
    description: List[RichText] = field(default_factory=list)
    icon: Optional[FileObject] = None
    cover: Optional[FileObject] = None
    object: str = "database"

    @classmethod
    def from_dict(cls, data: dict):
        created_by = data.pop("created_by")
        last_edited_by = data.pop("last_edited_by")
        icon = data.pop("icon")
        cover = data.pop("cover")
        parent = data.pop("parent")
        title = data.pop("title")
        description = data.pop("description")
        page = cls(
            properties=map_properties(data.pop("properties", {})),
            created_by=PartialUser.from_dict(created_by),
            last_edited_by=PartialUser.from_dict(last_edited_by),
            icon=FileObject.from_dict(icon) if icon else None,
            cover=FileObject.from_dict(cover) if cover else None,
            parent=Parent.from_dict(parent),
            title=[RichText.from_dict(data=r) for r in title],
            description=[RichText.from_dict(data=r) for r in description],
            **data,
        )

        return page

    def get_html(self) -> Optional[HtmlTag]:
        spans = []
        if title := self.title:
            spans.append(Span([], [rt.get_html() for rt in title]))
        if description := self.description:
            spans.append(Span([], [rt.get_html() for rt in description]))
        if spans:
            return Div([], spans)
        return None
