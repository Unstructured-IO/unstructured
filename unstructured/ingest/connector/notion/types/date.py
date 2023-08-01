# https://developers.notion.com/reference/property-value-object#date-property-values
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin


@dataclass
class Date(FromJSONMixin):
    start: str
    end: str
    time_zone: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
