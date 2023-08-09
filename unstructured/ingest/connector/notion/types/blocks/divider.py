# https://developers.notion.com/reference/block#divider
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class Divider(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls()

    def get_text(self) -> Optional[str]:
        return None
