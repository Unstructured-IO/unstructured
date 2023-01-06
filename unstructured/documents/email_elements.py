from abc import ABC
from datetime import datetime
import hashlib
from typing import Callable, List, Union
from unstructured.documents.elements import Element, Text, NoID


class EmailElement(Element):
    """An email element is a section of the email."""

    pass


class Name(EmailElement):
    """Base element for capturing free text from within document."""

    category = "Uncategorized"

    def __init__(
        self,
        name: str,
        text: str,
        element_id: Union[str, NoID] = NoID(),
    ):
        self.name: str = name
        self.text: str = text
        self.datestamp: datetime
        self.has_datestamp: bool = False

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        super().__init__(element_id=element_id)

    def set_datestamp(self, datestamp: datetime):
        self.datestamp = datestamp
        self.has_datestamp = True

    def __str__(self):
        return f"{self.name}: {self.text}"

    def __eq__(self, other):
        if self.has_datestamp:
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

        if not isinstance(cleaned_text, str):
            raise ValueError("Cleaner produced a non-string output.")

        if not isinstance(cleaned_name, str):
            raise ValueError("Cleaner produced a non-string output.")

        self.text = cleaned_text
        self.name = cleaned_name


class BodyText(List[Text]):
    """BodyText is an element consisting of multiple, well-formulated sentences. This
    excludes elements such titles, headers, footers, and captions. It is the body of an email."""

    category = "BodyText"

    pass


class Recipient(Name):
    """A text element for capturing the recipient information of an email"""

    category = "Recipient"

    pass


class Sender(Name):
    """A text element for capturing the sender information of an email"""

    category = "Sender"

    pass


class Subject(Text, EmailElement):
    """A text element for capturing the subject information of an email"""

    category = "Subject"

    pass


class MetaData(Name):
    """A text element for capturing header meta data of an email
    (miscellaneous data in the email)."""

    category = "MetaData"

    pass


class ReceivedInfo(Name):
    """A text element for capturing header information of an email (e.g. IP addresses, etc)."""

    category = "ReceivedInfo"

    pass


class Attachment(Name):
    """A text element for capturing the attachment name in an email (e.g. documents,
    images, etc)."""

    category = "Attachment"

    pass


class Email(ABC):
    """An email class with it's attributes"""

    def __init__(self):
        self.recipient = Recipient
        self.sender = Sender
        self.subject = Subject
        self.body = BodyText
        self.received_info: ReceivedInfo
        self.meta_data: MetaData
        self.attachment: List[Attachment]

    def __str__(self):
        return f"""
        Recipient: {self.recipient}
        Sender: {self.sender}
        Subject: {self.subject}

        Received Header Information:

        {self.received_info}

        Meta Data From Header:

        {self.meta_data}

        Body:

        {self.body}

        Attachment:

        {[file.name for file in self.attachment]}
        """
