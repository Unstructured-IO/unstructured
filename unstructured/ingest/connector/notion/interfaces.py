from abc import ABC, abstractmethod
from typing import Optional


class FromJSONMixin(ABC):
    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict):
        pass


class GetTextMixin(ABC):
    @abstractmethod
    def get_text(self) -> Optional[str]:
        pass


class BlockBase(FromJSONMixin, GetTextMixin):
    @staticmethod
    @abstractmethod
    def can_have_children() -> bool:
        pass


class DBPropertyBase(FromJSONMixin):
    pass


class DBCellBase(FromJSONMixin):
    pass
