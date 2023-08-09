# https://developers.notion.com/reference/block#link-to-page
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class LinkToPage(BlockBase):
    type: str
    page_id: Optional[str] = None
    database_id: Optional[str] = None

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        if page_id := self.page_id:
            return Div([], page_id)
        if database_id := self.database_id:
            return Div([], database_id)
        return None
