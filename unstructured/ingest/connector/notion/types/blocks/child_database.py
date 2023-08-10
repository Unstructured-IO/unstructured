# https://developers.notion.com/reference/block#child-database
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import HtmlTag, P

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class ChildDatabase(BlockBase):
    title: str

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        return P([], self.title)
