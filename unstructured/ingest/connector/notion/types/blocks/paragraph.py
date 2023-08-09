# https://developers.notion.com/reference/block#paragraph
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.tags import Br, Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Paragraph(BlockBase):
    color: str
    children: List[dict] = field(default_factory=list)
    rich_text: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        paragraph = cls(**data)
        paragraph.rich_text = [RichText.from_dict(rt) for rt in rich_text]
        return paragraph

    def get_html(self) -> Optional[HtmlTag]:
        if not self.rich_text:
            return Br()
        return Div([], [rt.get_html() for rt in self.rich_text])
