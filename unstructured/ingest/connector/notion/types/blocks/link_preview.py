# https://developers.notion.com/reference/block#link-preview
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class LinkPreview(BlockBase):
    url: str

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.url if self.url else None
