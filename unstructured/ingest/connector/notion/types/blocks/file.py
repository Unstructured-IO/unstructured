# https://developers.notion.com/reference/block#file
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.attributes import Href
from htmlBuilder.tags import A, Br, Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.file import External
from unstructured.ingest.connector.notion.types.file import File as FileContent
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class File(BlockBase):
    type: str
    external: Optional[External] = None
    file: Optional[FileContent] = None
    caption: List[RichText] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        caption = [RichText.from_dict(rt) for rt in data.pop("caption", [])]
        t = data["type"]
        file = cls(type=t, caption=caption)
        if t == "external":
            file.external = External.from_dict(data["external"])
        elif t == "file":
            file.file = FileContent.from_dict(data["file"])
        return file

    def get_html(self) -> Optional[HtmlTag]:
        texts = []
        if self.file:
            texts.append(A([Href(self.file.url)], self.file.url))
        if self.external:
            texts.append(A([Href(self.external.url)], self.external.url))
        if self.caption:
            texts.append(Div([], [rt.get_html() for rt in self.caption]))
        if not texts:
            return None
        joined = [Br()] * (len(texts) * 2 - 1)
        joined[0::2] = texts

        return Div([], joined)
