# https://developers.notion.com/reference/property-object#checkbox
from dataclasses import dataclass, field
from typing import Optional

from htmlBuilder.attributes import Checked, Type
from htmlBuilder.tags import Div, HtmlTag, Input

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase


@dataclass
class Checkbox(DBPropertyBase):
    id: str
    name: str
    type: str = "checkbox"
    checkbox: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class CheckboxCell(DBCellBase):
    id: str
    checkbox: bool
    name: Optional[str] = None
    type: str = "checkbox"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        check_input_attributes = [Type("checkbox")]
        if self.checkbox:
            check_input_attributes.append(Checked(""))
        return Div([], Input(check_input_attributes))
