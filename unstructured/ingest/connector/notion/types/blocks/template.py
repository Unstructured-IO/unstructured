# https://developers.notion.com/reference/block#template
from dataclasses import dataclass, field
from typing import List, Optional

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

    def get_text(self) -> Optional[str]:
        if not self.rich_text:
            return None
        rich_texts = [rt.get_text() for rt in self.rich_text]
        text = "\n".join([rt for rt in rich_texts if rt])
        return text if text else None
