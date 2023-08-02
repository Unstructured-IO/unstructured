# https://developers.notion.com/reference/property-object#multi-select
from dataclasses import dataclass, field
from typing import List, Optional

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class MultiSelectOption(FromJSONMixin):
    color: str
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class MultiSelectProp(FromJSONMixin):
    options: List[MultiSelectOption] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(options=[MultiSelectOption.from_dict(o) for o in data.get("options", [])])


@dataclass
class MultiSelect(DBPropertyBase):
    id: str
    name: str
    multi_select: List[MultiSelectProp]
    type: str = "multi_select"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            multi_select=data.pop("multi_select", {}),
            **data,
        )


@dataclass
class MultiSelectCell(DBCellBase):
    id: str
    type: str = "multi_select"
    multi_select: List[MultiSelectProp] = field(default_factory=list)
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            multi_select=data.pop("multi_select", {}),
            **data,
        )
