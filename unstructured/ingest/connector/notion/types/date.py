# https://developers.notion.com/reference/property-value-object#date-property-values
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin, GetTextMixin


@dataclass
class Date(FromJSONMixin, GetTextMixin):
    start: str
    end: str
    time_zone: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_text(self) -> Optional[str]:
        text = f"{self.start} - {self.end}"
        if self.time_zone:
            text += f" {self.time_zone}"
        return text
