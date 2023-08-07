from typing import Dict

from unstructured.ingest.connector.notion.interfaces import DBCellBase, DBPropertyBase

from .checkbox import Checkbox, CheckboxCell
from .created_by import CreatedBy, CreatedByCell
from .created_time import CreatedTime, CreatedTimeCell
from .date import Date, DateCell
from .email import Email, EmailCell
from .files import Files, FilesCell
from .formula import Formula, FormulaCell
from .last_edited_by import LastEditedBy, LastEditedByCell
from .last_edited_time import LastEditedTime, LastEditedTimeCell
from .multiselect import MultiSelect, MultiSelectCell
from .number import Number, NumberCell
from .people import People, PeopleCell
from .phone_number import PhoneNumber, PhoneNumberCell
from .relation import Relation, RelationCell
from .rich_text import RichText, RichTextCell
from .rollup import Rollup, RollupCell
from .select import Select, SelectCell
from .status import Status, StatusCell
from .title import Title, TitleCell
from .unique_id import UniqueID, UniqueIDCell
from .url import URL, URLCell
from .verification import Verification, VerificationCell

db_prop_type_mapping = {
    "checkbox": Checkbox,
    "created_by": CreatedBy,
    "created_time": CreatedTime,
    "date": Date,
    "email": Email,
    "files": Files,
    "formula": Formula,
    "last_edited_by": LastEditedBy,
    "last_edited_time": LastEditedTime,
    "multi_select": MultiSelect,
    "number": Number,
    "people": People,
    "phone_number": PhoneNumber,
    "relation": Relation,
    "rich_text": RichText,
    "rollup": Rollup,
    "select": Select,
    "status": Status,
    "title": Title,
    "unique_id": UniqueID,
    "url": URL,
    "verification": Verification,
}


def map_properties(props: Dict[str, dict]) -> Dict[str, DBPropertyBase]:
    mapped_dict = {}
    for k, v in props.items():
        try:
            mapped_dict[k] = db_prop_type_mapping[v["type"]].from_dict(v)  # type: ignore
        except KeyError as ke:
            raise KeyError(f"failed to map to associated database property -> {k}: {v}") from ke

    return mapped_dict


db_cell_type_mapping = {
    "checkbox": CheckboxCell,
    "created_by": CreatedByCell,
    "created_time": CreatedTimeCell,
    "date": DateCell,
    "email": EmailCell,
    "files": FilesCell,
    "formula": FormulaCell,
    "last_edited_by": LastEditedByCell,
    "last_edited_time": LastEditedTimeCell,
    "multi_select": MultiSelectCell,
    "number": NumberCell,
    "people": PeopleCell,
    "phone_number": PhoneNumberCell,
    "relation": RelationCell,
    "rich_text": RichTextCell,
    "rollup": RollupCell,
    "select": SelectCell,
    "status": StatusCell,
    "title": TitleCell,
    "unique_id": UniqueIDCell,
    "url": URLCell,
    "verification": VerificationCell,
}


def map_cells(props: Dict[str, dict]) -> Dict[str, DBCellBase]:
    mapped_dict = {}
    for k, v in props.items():
        try:
            t = v["type"]
            mapped_dict[k] = db_cell_type_mapping[t].from_dict(v)  # type: ignore
        except KeyError as ke:
            raise KeyError(f"failed to map to associated database property -> {k}: {v}") from ke

    return mapped_dict


__all__ = [
    "map_properties",
    "map_cells",
]
