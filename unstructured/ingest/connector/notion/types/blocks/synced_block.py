# https://developers.notion.com/reference/block#synced-block
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import BlockBase


@dataclass
class OriginalSyncedBlock(BlockBase):
    synced_from: Optional[str] = None
    children: List[dict] = field(default_factory=list)

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(children=data["children"])


@dataclass
class DuplicateSyncedBlock(BlockBase):
    type: str
    block_id: str

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class SyncBlock(BlockBase):
    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        if "synced_from" in data:
            return OriginalSyncedBlock.from_dict(data)
        else:
            return DuplicateSyncedBlock.from_dict(data)
