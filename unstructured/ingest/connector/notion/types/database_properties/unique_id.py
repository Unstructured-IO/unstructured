# https://developers.notion.com/reference/property-object#title
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class UniqueID(DBPropertyBase):
    id: str
    name: str
    type: str = "unique_id"
    unique_id: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UniqueIDCellData(FromJSONMixin):
    prefix: str
    number: int

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class UniqueIDCell(DBCellBase):
    id: str
    unique_id: UniqueIDCellData
    type: str = "title"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(unique_id=UniqueIDCellData.from_dict(data.pop("unique_id")), **data)

    def get_text(self) -> Optional[str]:
        return f"{self.unique_id.prefix}-{self.unique_id.number}"
