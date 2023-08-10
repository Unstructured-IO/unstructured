# https://developers.notion.com/reference/block#embed
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.attributes import Href
from htmlBuilder.tags import A, Br, Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Embed(BlockBase):
    url: str
    caption: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(caption=[RichText.from_dict(d) for d in data.pop("caption", [])], **data)

    def get_html(self) -> Optional[HtmlTag]:
        texts = []
        if self.url:
            texts.append(A([Href(self.url)], self.url))
        if self.caption:
            texts.append(Div([], [rt.get_html() for rt in self.caption]))
        if not texts:
            return None
        joined = [Br()] * (len(texts) * 2 - 1)
        joined[0::2] = texts

        return Div([], joined)
