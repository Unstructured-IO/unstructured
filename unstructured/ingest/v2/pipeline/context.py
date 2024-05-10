from dataclasses import dataclass, field
from multiprocessing.managers import DictProxy
from typing import Optional

from unstructured.ingest.v2.interfaces import ProcessorConfig


@dataclass
class PipelineContext(ProcessorConfig):
    _statuses: Optional[DictProxy] = field(init=False, default=None)

    @property
    def statuses(self) -> DictProxy:
        if self._statuses is None:
            raise ValueError("statuses never initialized")
        return self._statuses

    @statuses.setter
    def statuses(self, value: DictProxy):
        self._statuses = value
