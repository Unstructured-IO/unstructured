from abc import ABC, abstractmethod
from typing import Optional

from htmlBuilder.tags import HtmlTag


class FromJSONMixin(ABC):
    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict):
        pass


class GetHTMLMixin(ABC):
    @abstractmethod
    def get_html(self) -> Optional[HtmlTag]:
        pass


class BlockBase(FromJSONMixin, GetHTMLMixin):
    @staticmethod
    @abstractmethod
    def can_have_children() -> bool:
        pass


class DBPropertyBase(FromJSONMixin):
    pass


class DBCellBase(FromJSONMixin, GetHTMLMixin):
    pass
