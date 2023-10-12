# https://developers.notion.com/reference/page
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin
from unstructured.ingest.connector.notion.types.file import FileObject
from unstructured.ingest.connector.notion.types.parent import Parent
from unstructured.ingest.connector.notion.types.user import PartialUser


@dataclass
class Page(FromJSONMixin):
    id: str
    created_time: str
    created_by: PartialUser
    last_edited_time: str
    last_edited_by: PartialUser
    archived: bool
    properties: dict
    parent: Parent
    url: str
    public_url: str
    request_id: Optional[str] = None
    object: str = "page"
    icon: Optional[FileObject] = None
    cover: Optional[FileObject] = None

    @classmethod
    def from_dict(cls, data: dict):
        created_by = data.pop("created_by")
        last_edited_by = data.pop("last_edited_by")
        icon = data.pop("icon")
        cover = data.pop("cover")
        parent = data.pop("parent")
        page = cls(
            created_by=PartialUser.from_dict(created_by),
            last_edited_by=PartialUser.from_dict(last_edited_by),
            icon=FileObject.from_dict(icon) if icon else None,
            cover=FileObject.from_dict(cover) if cover else None,
            parent=Parent.from_dict(parent),
            **data,
        )

        return page
