from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BaseProcess(ABC):
    def is_async(self) -> bool:
        return False

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        pass

    async def run_async(self, **kwargs: Any) -> Any:
        return self.run(**kwargs)

    def check_connection(self):
        # If the process requires external connections, run a quick check
        pass
