# https://developers.notion.com/reference/property-object#multi-select
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.attributes import Style
from htmlBuilder.tags import Div, HtmlTag, Span

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
    multi_select: MultiSelectProp
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
    multi_select: List[MultiSelectOption]
    type: str = "multi_select"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            multi_select=[MultiSelectOption.from_dict(o) for o in data.pop("multi_select", [])],
            **data,
        )

    def get_html(self) -> Optional[HtmlTag]:
        if not self.multi_select:
            return None
        option_spans = []
        for option in self.multi_select:
            option_attributes = []
            if option.color and option.color != "default":
                option_attributes.append(Style(f"color: {option.color}"))
            option_spans.append(Span(option_attributes, option.name))
        return Div([], option_spans)
