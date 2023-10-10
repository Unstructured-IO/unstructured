# https://developers.notion.com/reference/page
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import HtmlTag

from unstructured.ingest.connector.notion.interfaces import (
    BlockBase,
    FromJSONMixin,
    GetHTMLMixin,
)
from unstructured.ingest.connector.notion.types import blocks
from unstructured.ingest.connector.notion.types.parent import Parent
from unstructured.ingest.connector.notion.types.user import PartialUser

block_type_mapping = {
    "bookmark": blocks.Bookmark,
    "breadcrumb": blocks.Breadcrumb,
    "bulleted_list_item": blocks.BulletedListItem,
    "callout": blocks.Callout,
    "child_database": blocks.ChildDatabase,
    "child_page": blocks.ChildPage,
    "code": blocks.Code,
    "column": blocks.Column,
    "column_list": blocks.ColumnList,
    "divider": blocks.Divider,
    "heading_1": blocks.Heading,
    "heading_2": blocks.Heading,
    "heading_3": blocks.Heading,
    "embed": blocks.Embed,
    "equation": blocks.Equation,
    "file": blocks.File,
    "image": blocks.Image,
    "link_preview": blocks.LinkPreview,
    "link_to_page": blocks.LinkToPage,
    "numbered_list_item": blocks.NumberedListItem,
    "paragraph": blocks.Paragraph,
    "pdf": blocks.PDF,
    "quote": blocks.Quote,
    "synced_block": blocks.SyncBlock,
    "table": blocks.Table,
    "table_of_contents": blocks.TableOfContents,
    "table_row": blocks.TableRow,
    "template": blocks.Template,
    "to_do": blocks.ToDo,
    "toggle": blocks.Toggle,
    "unsupported": blocks.Unsupported,
    "video": blocks.Video,
}


@dataclass
class Block(FromJSONMixin, GetHTMLMixin):
    id: str
    type: str
    created_time: str
    created_by: PartialUser
    last_edited_time: str
    last_edited_by: PartialUser
    archived: bool
    has_children: bool
    parent: Parent
    block: BlockBase
    object: str = "block"
    request_id: Optional[str] = None

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, type={self.type})"

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        block_data = data.pop(t)
        created_by = data.pop("created_by")
        last_edited_by = data.pop("last_edited_by")
        parent = data.pop("parent")
        try:
            block = cls(
                created_by=PartialUser.from_dict(created_by),
                last_edited_by=PartialUser.from_dict(last_edited_by),
                parent=Parent.from_dict(parent),
                block=block_type_mapping[t].from_dict(block_data),  # type: ignore
                **data,
            )
        except KeyError as ke:
            raise KeyError(f"failed to map to associated block type -> {t}: {block_data}") from ke
        except TypeError as te:
            raise TypeError(f"failed to map to associated block type -> {t}: {block_data}") from te

        return block

    def get_html(self) -> Optional[HtmlTag]:
        if self.block:
            return self.block.get_html()
        return None
