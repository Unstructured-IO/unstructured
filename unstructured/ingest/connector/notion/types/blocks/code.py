# https://developers.notion.com/reference/block#code
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.tags import Br, Div, HtmlTag
from htmlBuilder.tags import Code as HtmlCode

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Code(BlockBase):
    language: str
    rich_text: List[RichText] = field(default_factory=list)
    caption: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        caption = data.pop("caption", [])
        return cls(
            language=data["language"],
            rich_text=[RichText.from_dict(rt) for rt in rich_text],
            caption=[RichText.from_dict(c) for c in caption],
        )

    def get_html(self) -> Optional[HtmlTag]:
        texts = []
        if self.rich_text:
            texts.append(HtmlCode([], [rt.get_html() for rt in self.rich_text]))
        if self.caption:
            texts.append(Div([], [rt.get_html() for rt in self.caption]))
        if not texts:
            return None
        joined = [Br()] * (len(texts) * 2 - 1)
        joined[0::2] = texts

        return Div([], joined)
