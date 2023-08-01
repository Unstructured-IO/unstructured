# https://developers.notion.com/reference/block#table
from dataclasses import dataclass, field
from typing import List

from unstructured.ingest.connector.notion.interfaces import BlockBase
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


# https://developers.notion.com/reference/block#table-rows
@dataclass
class TableRow(BlockBase):
    cells: List[RichText] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        cells = data.get("cells", [])
        return cls(cells=[RichText.from_dict(c) for c in cells])
