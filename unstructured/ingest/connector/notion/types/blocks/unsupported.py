from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class Unsupported(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls()

    def get_html(self) -> Optional[HtmlTag]:
        return None
