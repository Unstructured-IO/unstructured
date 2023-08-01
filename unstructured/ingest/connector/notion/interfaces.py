from abc import ABC, abstractmethod


class FromJSONMixin(ABC):
    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict):
        pass


class BlockBase(FromJSONMixin):
    @staticmethod
    @abstractmethod
    def can_have_children() -> bool:
        pass
