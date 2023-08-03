# https://developers.notion.com/reference/property-object#formula
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import (
    DBCellBase,
    DBPropertyBase,
    FromJSONMixin,
)


@dataclass
class FormulaProp(FromJSONMixin):
    expression: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class Formula(DBPropertyBase):
    id: str
    name: str
    formula: FormulaProp
    type: str = "formula"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(formula=FormulaProp.from_dict(data.pop("formula", {})), **data)


@dataclass
class FormulaCell(DBCellBase):
    id: str
    formula: dict
    type: str = "formula"
    name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        formula = self.formula
        t = formula.get("type")
        return formula[t]
