# https://developers.notion.com/reference/block#file
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class File(BlockBase):
    type: str
    rich_text: List[RichText] = field(default_factory=list)
    file: dict = field(default_factory=dict)

    @staticmethod
    def can_have_children() -> bool:
        return False

    @classmethod
    def from_dict(cls, data: dict):
        rich_text = data.pop("rich_text", [])
        file = cls(**data)
        file.rich_text = [RichText.from_dict(rt) for rt in rich_text]
        return file

    def get_text(self) -> Optional[str]:
        if not self.rich_text:
            return None
        rich_texts = [rt.get_text() for rt in self.rich_text]
        text = "\n".join([rt for rt in rich_texts if rt])
        return text if text else None
