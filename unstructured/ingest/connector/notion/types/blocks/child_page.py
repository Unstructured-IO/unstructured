# https://developers.notion.com/reference/block#child-page
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase, GetTextMixin


@dataclass
class ChildPage(BlockBase, GetTextMixin):
    title: str

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.title if self.title else None
