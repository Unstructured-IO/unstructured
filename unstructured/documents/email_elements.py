from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import Callable, Optional

from unstructured.documents.elements import Text


class NoDatestamp(ABC):
    """Class to indicate that an element do not have a datetime stamp."""


class EmailElement(Text):
    """An email element is a section of the email."""


class Name(EmailElement):
    """Base element for capturing free text from within document."""

    category = "Uncategorized"

    def __init__(
        self,
        name: str,
        text: str,
        datestamp: datetime | NoDatestamp = NoDatestamp(),
        element_id: Optional[str] = None,
    ):
        self.name: str = name

        super().__init__(text=text, element_id=element_id)

        if isinstance(datestamp, datetime):
            self.datestamp: datetime = datestamp

    def has_datestamp(self):
        return "self.datestamp" in globals()

    def __str__(self):
        return f"{self.name}: {self.text}"

    def __eq__(self, other) -> bool:
        if self.has_datestamp():
            return (
                self.name == other.name
                and self.text == other.text
                and self.datestamp == other.datestamp
            )
        return self.name == other.name and self.text == other.text

    def apply(self, *cleaners: Callable):
        """Applies a cleaning brick to the text element. The function that's passed in
        should take a string as input and produce a string as output."""
        cleaned_text = self.text
        cleaned_name = self.name

        for cleaner in cleaners:
            cleaned_text = cleaner(cleaned_text)
            cleaned_name = cleaner(cleaned_name)

        if not isinstance(cleaned_text, str) or not isinstance(cleaned_name, str):
            raise ValueError("Cleaner produced a non-string output.")

        self.text = cleaned_text
        self.name = cleaned_name


class BodyText(list[Text]):
    """BodyText is an element consisting of multiple, well-formulated sentences. This
    excludes elements such titles, headers, footers, and captions. It is the body of an email."""

    category = "BodyText"


class Recipient(Name):
    """A text element for capturing the recipient information of an email"""

    category = "Recipient"


class Sender(Name):
    """A text element for capturing the sender information of an email"""

    category = "Sender"


class Subject(EmailElement):
    """A text element for capturing the subject information of an email"""

    category = "Subject"


class MetaData(Name):
    """A text element for capturing header meta data of an email
    (miscellaneous data in the email)."""

    category = "MetaData"


class ReceivedInfo(Name):
    """A text element for capturing header information of an email (e.g. IP addresses, etc)."""

    category = "ReceivedInfo"


class Attachment(Name):
    """A text element for capturing the attachment name in an email (e.g. documents,
    images, etc)."""

    category = "Attachment"
