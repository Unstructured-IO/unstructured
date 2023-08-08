# https://developers.notion.com/reference/block#template
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Template(BlockBase):
    children: List[dict] = field(default_factory=list)
    rich_text: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        template = cls(**data)
        template.rich_text = [RichText.from_dict(rt) for rt in rich_text]
        return template

    def get_html(self) -> Optional[HtmlTag]:
        if not self.rich_text:
            return None
        return Div([], [rt.get_html() for rt in self.rich_text])
