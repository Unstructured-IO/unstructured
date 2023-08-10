# https://developers.notion.com/reference/block#column-list-and-column
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class ColumnList(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls()

    def get_html(self) -> Optional[HtmlTag]:
        return None


@dataclass
class Column(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls()

    def get_html(self) -> Optional[HtmlTag]:
        return None
