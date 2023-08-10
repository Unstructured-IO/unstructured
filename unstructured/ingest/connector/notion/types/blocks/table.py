# https://developers.notion.com/reference/block#table
from dataclasses import dataclass, field
from typing import List, Optional

from htmlBuilder.tags import HtmlTag, Td, Th, Tr

from unstructured.ingest.connector.notion.interfaces import (
    BlockBase,
    FromJSONMixin,
)
from unstructured.ingest.connector.notion.types.rich_text import RichText


@dataclass
class Table(BlockBase):
    table_width: int
    has_column_header: bool
    has_row_header: bool

    @staticmethod
    def can_have_children() -> bool:
        return True

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        return None


@dataclass
class TableCell(FromJSONMixin):
    rich_texts: List[RichText]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(rich_texts=[RichText.from_dict(rt) for rt in data.pop("rich_texts", [])])

    def get_html(self, is_header: bool) -> Optional[HtmlTag]:
        if is_header:
            return Th([], [rt.get_html() for rt in self.rich_texts])
        else:
            return Td([], [rt.get_html() for rt in self.rich_texts])


# https://developers.notion.com/reference/block#table-rows
@dataclass
class TableRow(BlockBase):
    is_header: bool = False
    cells: List[TableCell] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        cells = data.get("cells", [])
        return cls(cells=[TableCell.from_dict({"rich_texts": c}) for c in cells])

    @staticmethod
    def can_have_children() -> bool:
        return False

    def get_html(self) -> Optional[HtmlTag]:
        return Tr([], [cell.get_html(is_header=self.is_header) for cell in self.cells])
