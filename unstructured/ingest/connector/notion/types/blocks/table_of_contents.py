# https://developers.notion.com/reference/block#table-of-contents
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class TableOfContents(BlockBase):
    color: str

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return None
