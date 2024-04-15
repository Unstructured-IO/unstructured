from dataclasses import dataclass

from more_itertools import first


@dataclass
class SimpleTableCell:
    x: int
    y: int
    w: int
    h: int
    content: str = ""

    def to_dict(self):
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h, "content": self.content}

    @classmethod
    def from_table_transformer_cell(cls, tatr_table_cell: dict[str, list[int] | str]):
        """
        Args:
            tatr_table_cell (dict):
                Cell in a format returned by Table Transformer model, for example:
                    {
                        "row_nums": [1,2,3],
                        "column_nums": [2],
                        "cell text": "Text inside cell"
                    }
        """
        rows_sorted = sorted(tatr_table_cell["row_nums"])
        columns_sorted = sorted(tatr_table_cell["column_nums"])

        x = first(columns_sorted)
        y = first(rows_sorted)

        width = len(columns_sorted)
        height = len(rows_sorted)

        return cls(x=x, y=y, w=width, h=height, content=tatr_table_cell["cell text"])
