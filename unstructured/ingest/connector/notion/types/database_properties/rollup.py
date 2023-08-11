# https://developers.notion.com/reference/property-object#rollup
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import Div, HtmlTag, Span

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class RollupProp(FromJSONMixin):
    function: str
    relation_property_id: str
    relation_property_name: str
    rollup_property_id: str
    rollup_property_name: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class Rollup(DBPropertyBase):
    id: str
    name: str
    rollup: RollupProp
    type: str = "rollup"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(rollup=RollupProp.from_dict(data.pop("rollup")), **data)


@dataclass
class RollupCell(DBCellBase):
    id: str
    rollup: dict
    type: str = "rollup"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        rollup = self.rollup
        t = rollup.get("type")
        v = rollup[t]
        if isinstance(v, list):
            return Div([], [Span([], str(x)) for x in v])
        return Div([], str(v))
