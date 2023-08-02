# https://developers.notion.com/reference/property-object#last-edited-by
from dataclasses import dataclass

from unstructured.ingest.connector.notion.interfaces import DBPropertyBase


@dataclass
class LastEditedBy(DBPropertyBase):
    @classmethod
    def from_dict(cls, data: dict):
        return cls()
