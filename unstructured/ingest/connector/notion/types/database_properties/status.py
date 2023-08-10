# https://developers.notion.com/reference/property-object#status
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.attributes import Style
from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class StatusOption(FromJSONMixin):
    color: str
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class StatusGroup(FromJSONMixin):
    color: str
    id: str
    name: str
    option_ids: List[str] = field(default_factory=List[str])

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class StatusProp(FromJSONMixin):
    options: List[StatusOption] = field(default_factory=list)
    groups: List[StatusGroup] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            options=[StatusOption.from_dict(o) for o in data.get("options", [])],
            groups=[StatusGroup.from_dict(g) for g in data.get("groups", [])],
        )


@dataclass
class Status(DBPropertyBase):
    id: str
    name: str
    status: StatusProp
    type: str = "status"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(status=StatusProp.from_dict(data.pop("status", {})), **data)


@dataclass
class StatusCell(DBCellBase):
    id: str
    status: Optional[StatusOption]
    type: str = "status"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(status=StatusOption.from_dict(data.pop("status", {})), **data)

    def get_html(self) -> Optional[HtmlTag]:
        if status := self.status:
            select_attr = []
            if status.color and status.color != "default":
                select_attr.append(Style(f"color: {status.color}"))
            return Div(select_attr, status.name)
        return None
