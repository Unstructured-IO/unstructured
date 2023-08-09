# https://developers.notion.com/reference/property-object#url
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
    GetTextMixin,
)
from unstructured.ingest.connector.notion.types.date import Date
from unstructured.ingest.connector.notion.types.user import People


@dataclass
class Verification(DBPropertyBase):
    id: str
    name: str
    type: str = "verification"
    verification: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class VerificationData(FromJSONMixin, GetTextMixin):
    state: Optional[str]
    verified_by: Optional[People]
    date: Optional[Date]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        texts: List[str] = []
        if self.state:
            texts.append(self.state)
        if self.verified_by:
            verified_by_text = self.verified_by.get_text()
            if verified_by_text:
                texts.append(verified_by_text)
        if self.date:
            date_text = self.date.get_text()
            if date_text:
                texts.append(date_text)
        return ", ".join(texts) if texts else None


@dataclass
class VerificationCell(DBCellBase):
    id: str
    verification: Optional[VerificationData]
    name: Optional[str] = None
    type: str = "verification"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        texts = []
        if self.name:
            texts.append(self.name)
        if self.verification:
            verification_text = self.verification.get_text()
            if verification_text:
                texts.append(verification_text)
        return ", ".join(texts)
