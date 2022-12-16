from abc import ABC
import hashlib
from typing import Callable, Union
from unstructured.documents.elements import Element, Text, NoID

class EmailElement(Element):
    """An email element is a section of the email."""

    pass

    
class Name(EmailElement):
    """Base element for capturing free text from within document."""

    category = "Uncategorized"

    def __init__(self, name: str, text: str, element_id: Union[str, NoID] = NoID()):
        self.name = str = name
        self.text: str = text

        if isinstance(element_id, NoID):
            # NOTE(robinson) - Cut the SHA256 hex in half to get the first 128 bits
            element_id = hashlib.sha256(text.encode()).hexdigest()[:32]

        super().__init__(element_id=element_id)
        

    def __str__(self):
        return f"{self.name}: {self.text}"

    def __eq__(self, other):
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

class BodyText(Text):
    """BodyText is an element consisting of multiple, well-formulated sentences. This
    excludes elements such titles, headers, footers, and captions. It is the body of an email."""

    category = "BodyText"

    pass


class ToHeader(Text):
    """A text element for capturing header information of an email (e.g. Subject, 
    To, From, etc)."""

    category = "ToHeader"

    pass

class FromHeader(Text):
    """A text element for capturing header information of an email (e.g. Subject, 
    To, From, etc)."""

    category = "FromHeader"

    pass

class SubjectHeader(Text):
    """A text element for capturing header information of an email (e.g. Subject, 
    To, From, etc)."""

    category = "SubjectHeader"

    pass

class ReceivedHeader(Text):
    """A text element for capturing header information of an email (e.g. Subject, 
    To, From, etc)."""

    category = "ReceivedHeader"

    pass

class MetaDataHeader(Name):
    """A text element for capturing header information of an email (e.g. Subject, 
    To, From, etc)."""

    category = "MetaDataHeader"

    pass

class Attachment(Text):
    """A text element for capturing header information of an email (e.g. Subject, 
    To, From, etc)."""

    category = "Attachment"

    pass