# https://developers.notion.com/reference/file-object
from dataclasses import dataclass
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin


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
class FileObject(FromJSONMixin):
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
