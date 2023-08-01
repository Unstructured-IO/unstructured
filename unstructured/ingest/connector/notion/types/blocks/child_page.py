# https://developers.notion.com/reference/block#child-page
from dataclasses import dataclass

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class ChildPage(BlockBase):
    title: str

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
