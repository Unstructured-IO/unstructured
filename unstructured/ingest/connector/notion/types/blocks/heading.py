# https://developers.notion.com/reference/block#headings
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.attributes import Style
from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Heading(BlockBase):
    color: str
    is_toggleable: bool
    rich_text: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        heading = cls(**data)
        heading.rich_text = [RichText.from_dict(rt) for rt in rich_text]
        return heading

    def get_html(self) -> Optional[HtmlTag]:
        if not self.rich_text:
            return None

        texts = [rt.get_html() for rt in self.rich_text]
        attributes = []
        if self.color and self.color != "default":
            attributes.append(Style(f"color: {self.color}"))
        return Div(attributes, texts)
