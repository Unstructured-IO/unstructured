# https://developers.notion.com/reference/block#bookmark
from dataclasses import dataclass, field
from typing import List, Optional

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

    def get_text(self) -> Optional[str]:
        if not self.caption:
            return None
        rich_texts = [rt.get_text() for rt in self.caption]
        text = "\n".join([rt for rt in rich_texts if rt])
        return text if text else None
