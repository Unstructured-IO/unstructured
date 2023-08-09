# https://developers.notion.com/reference/property-object#relation
from dataclasses import dataclass
from typing import Optional
from urllib.parse import unquote

from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class DualProperty(FromJSONMixin):
    synced_property_id: str
    synced_property_name: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class RelationProp(FromJSONMixin):
    database_id: str
    type: str
    dual_property: DualProperty

    @classmethod
    def from_dict(cls, data: dict):
        t = data.get("type")
        if t == "dual_property":
            dual_property = DualProperty.from_dict(data.pop(t))
        else:
            raise ValueError(f"{t} type not recognized")

        return cls(dual_property=dual_property, **data)


@dataclass
class Relation(DBPropertyBase):
    id: str
    name: str
    relation: RelationProp
    type: str = "relation"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(relation=RelationProp.from_dict(data.pop("relation")), **data)


@dataclass
class RelationCell(DBCellBase):
    id: str
    has_more: bool
    relation: list
    type: str = "relation"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        return Div([], unquote(self.id))
