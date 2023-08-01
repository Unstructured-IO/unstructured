# https://developers.notion.com/reference/page
from dataclasses import dataclass

from unstructured.ingest.connector.notion.interfaces import BlockBase, FromJSONMixin
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
    "column": blocks.Column,
    "column_list": blocks.ColumnList,
    "divider": blocks.Divider,
    "embed": blocks.Embed,
    "equation": blocks.Equation,
    "file": blocks.File,
    "image": blocks.Image,
    "link_preview": blocks.LinkPreview,
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
    "video": blocks.Video,
}


@dataclass
class Block(FromJSONMixin):
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

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        block_data = data.pop(t)
        created_by = data.pop("created_by")
        last_edited_by = data.pop("last_edited_by")
        parent = data.pop("parent")
        block = cls(
            created_by=PartialUser.from_dict(created_by),
            last_edited_by=PartialUser.from_dict(last_edited_by),
            parent=Parent.from_dict(parent),
            block=block_type_mapping.get(t).from_dict(block_data),  # type: ignore
            **data,
        )

        return block


if __name__ == "__main__":
    print(type(blocks.Table))
