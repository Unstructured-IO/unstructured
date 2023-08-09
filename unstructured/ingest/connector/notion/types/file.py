# https://developers.notion.com/reference/file-object
from dataclasses import dataclass
from typing import Optional

from htmlBuilder.attributes import Href
from htmlBuilder.tags import A, HtmlTag

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin, GetHTMLMixin


@dataclass
class External(FromJSONMixin):
    url: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class File(FromJSONMixin):
    url: str
    expiry_time: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class FileObject(FromJSONMixin, GetHTMLMixin):
    type: str
    external: Optional[External] = None
    file: Optional[File] = None

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        file_object = cls(type=t)
        if t == "external":
            file_object.external = External.from_dict(data["external"])
        elif t == "file":
            file_object.file = File.from_dict(data["file"])
        return file_object

    def get_html(self) -> Optional[HtmlTag]:
        if self.file:
            return A([Href(self.file.url)], self.file.url)
        if self.external:
            return A([Href(self.external.url)], self.external.url)
        return None
