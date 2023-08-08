# https://developers.notion.com/reference/property-value-object#date-property-values
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.tags import Div, HtmlTag

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin, GetHTMLMixin


@dataclass
class Date(FromJSONMixin, GetHTMLMixin):
    start: str
    end: Optional[str] = None
    time_zone: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    def get_html(self) -> Optional[HtmlTag]:
        text = f"{self.start}"
        if end := self.end:
            text += f" - {end}"
        if self.time_zone:
            text += f" {self.time_zone}"
        return Div([], text)
