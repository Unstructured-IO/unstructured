# https://developers.notion.com/reference/parent-object
from dataclasses import dataclass

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin


# https://developers.notion.com/reference/parent-object#database-parent
@dataclass
class DatabaseParent(FromJSONMixin):
    database_id: str
    type: str = "database_id"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(database_id=data["database_id"])


# https://developers.notion.com/reference/parent-object#page-parent
@dataclass
class PageParent(FromJSONMixin):
    page_id: str
    type: str = "page_id"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(page_id=data["page_id"])


# https://developers.notion.com/reference/parent-object#workspace-parent
@dataclass
class WorkspaceParent(FromJSONMixin):
    type: str = "workspace"
    workspace: bool = True

    @classmethod
    def from_dict(cls, data: dict):
        return cls()


# https://developers.notion.com/reference/parent-object#block-parent
@dataclass
class BlockParent(FromJSONMixin):
    block_id: str
    type: str = "block_id"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(block_id=data["block_id"])


@dataclass
class Parent(FromJSONMixin):
    block_id: str
    type: str = "block_id"

    @classmethod
    def from_dict(cls, data: dict):
        t = data["type"]
        if t == "database_id":
            return DatabaseParent.from_dict(data)
        elif t == "page_id":
            return PageParent.from_dict(data)
        elif t == "workspace":
            return WorkspaceParent.from_dict(data)
        elif t == "block_id":
            return BlockParent.from_dict(data)
