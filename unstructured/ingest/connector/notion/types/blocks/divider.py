# https://developers.notion.com/reference/block#divider
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.attributes import Style
from htmlBuilder.tags import Hr, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class Divider(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls()

    def get_html(self) -> Optional[HtmlTag]:
        return Hr([Style("border-top: 3px solid #bbb")])
