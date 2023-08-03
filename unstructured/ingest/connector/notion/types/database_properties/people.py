# https://developers.notion.com/reference/property-object#people
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase
from unstructured.ingest.connector.notion.types.user import People as PeopleType


@dataclass
class People(DBPropertyBase):
    id: str
    name: str
    type: str = "people"
    people: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class PeopleCell(DBCellBase):
    id: str
    people: List[PeopleType]
    type: str = "people"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(people=[PeopleType.from_dict(p) for p in data.pop("people", {})], **data)

    def get_text(self) -> Optional[str]:
        texts = [p.get_text() for p in self.people]
        return ",".join([t for t in texts if t])
