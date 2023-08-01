# https://developers.notion.com/reference/block#bulleted-list-item
from dataclasses import dataclass, field
from typing import List

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class BulletedListItem(BlockBase):
    color: str
    children: List[dict] = field(default_factory=list)
    rich_text: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        return cls(
            color=data["color"],
            children=data["children"],
            rich_text=[RichText.from_dict(rt) for rt in rich_text],
        )
