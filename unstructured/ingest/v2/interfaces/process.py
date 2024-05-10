from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BaseProcess(ABC):

    def is_async(self) -> bool:
        return False

    @abstractmethod
    def run(self, **kwargs) -> Any:
        pass

    async def run_async(self, **kwargs) -> Any:
        return self.run(**kwargs)
