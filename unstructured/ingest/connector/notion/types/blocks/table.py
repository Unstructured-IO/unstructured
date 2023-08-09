# https://developers.notion.com/reference/block#table
from dataclasses import dataclass, field
from typing import List, Optional

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

    def get_text(self) -> Optional[str]:
        return None


# https://developers.notion.com/reference/block#table-rows
@dataclass
class TableRow(BlockBase):
    cells: List[List[RichText]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        cells = data.get("cells", [])
        return cls(cells=[[RichText.from_dict(cc) for cc in c] for c in cells])

    def get_text(self) -> Optional[str]:
        texts = []
        for cell in self.cells:
            texts.extend([rt.get_text() for rt in cell])
        text = "\n".join([t for t in texts if t])
        return text if text else None

    @staticmethod
    def can_have_children() -> bool:
        return False
