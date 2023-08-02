# https://developers.notion.com/reference/property-object#last-edited-time
from dataclasses import dataclass, field

from unstructured.ingest.connector.notion.interfaces import DBPropertyBase


@dataclass
class LastEditedTime(DBPropertyBase):
    id: str
    name: str
    type: str = "last_edited_time"
    last_edited_time: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
