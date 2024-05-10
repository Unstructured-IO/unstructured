import hashlib
import json
from dataclasses import dataclass
from typing import Generator, Optional, TypeVar

from unstructured.ingest.v2.interfaces.indexer import Indexer
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep

index_type = TypeVar("index_type", bound=Indexer)

STEP_ID = "index"


@dataclass
class IndexStepResponse:
    record_id: str
    path: str


@dataclass(kw_only=True)
class IndexStep(PipelineStep):
    identifier: str = STEP_ID
    process: index_type

    def run(self) -> Generator[IndexStepResponse, None, None]:
        for file_data in self.process.run():
            record_hash = self.get_hash(extras=[file_data.identifier])
            filename = f"{record_hash}.json"
            filepath = (self.cache_dir / filename).resolve()
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(str(filepath), "w") as f:
                json.dump(file_data.to_dict(), f, indent=2)
            yield IndexStepResponse(record_id=record_hash, path=str(filepath))

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(self.process.index_config.to_dict())
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
