# https://developers.notion.com/reference/block#bookmark
from dataclasses import dataclass, field
from typing import List

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Bookmark(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return False

    url: str
    caption: List[RichText] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        captions = data.pop("caption", [])
        return cls(
            url=data["url"],
            caption=[RichText.from_dict(c) for c in captions],
        )
