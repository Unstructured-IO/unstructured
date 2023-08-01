# https://developers.notion.com/reference/user
from dataclasses import dataclass, field
from typing import Optional

from unstructured.ingest.connector.notion.interfaces import FromJSONMixin


@dataclass
class PartialUser(FromJSONMixin):
    id: str
    object: str = "user"

    @classmethod
    def from_dict(cls, data: dict):
        return cls(id=data["id"])


@dataclass
class User(FromJSONMixin):
    object: dict
    id: str
    type: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class People(User):
    person: dict = field(default_factory=dict)


class Bots(User):
    bot: dict
    owner: dict
    type: str
    workspace_name: str
