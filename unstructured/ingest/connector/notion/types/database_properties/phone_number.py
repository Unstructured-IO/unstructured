# https://developers.notion.com/reference/property-object#phone-number
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase


@dataclass
class PhoneNumber(DBPropertyBase):
    id: str
    name: str
    type: str = "phone_number"
    phone_number: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class PhoneNumberCell(DBCellBase):
    id: str
    phone_number: str
    name: Optional[str] = None
    type: str = "phone_number"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        return self.phone_number
