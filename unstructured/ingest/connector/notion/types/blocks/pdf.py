# https://developers.notion.com/reference/block#pdf
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.file import External, File
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class PDF(BlockBase):
    type: str
    caption: List[RichText] = field(default_factory=list)
    external: Optional[External] = None
    file: Optional[File] = None

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        caption = data.pop("caption", [])
        t = data["type"]
        paragraph = cls(type=t)
        paragraph.caption = [RichText.from_dict(c) for c in caption]
        if t == "external":
            paragraph.external = External.from_dict(data["external"])
        elif t == "file":
            paragraph.file = File.from_dict(data["file"])
        return paragraph

    def get_text(self) -> Optional[str]:
        if not self.caption:
            return None
        rich_texts = [rt.get_text() for rt in self.caption]
        text = "\n".join([rt for rt in rich_texts if rt])
        return text if text else None
