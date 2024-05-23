import hashlib
import json
from dataclasses import dataclass
from typing import Generator, Optional, TypeVar

from unstructured.ingest.v2.interfaces.indexer import Indexer
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict

IndexerT = TypeVar("IndexerT", bound=Indexer)

STEP_ID = "index"


@dataclass
class IndexStep(PipelineStep):
    process: IndexerT
    identifier: str = STEP_ID

    def __str__(self):
        return f"{self.identifier} ({self.process.__class__.__name__})"

    def __post_init__(self):
        config = (
            sterilize_dict(self.process.index_config.to_dict(redact_sensitive=True))
            if self.process.index_config
            else None
        )
        connection_config = (
            sterilize_dict(self.process.connection_config.to_dict(redact_sensitive=True))
            if self.process.connection_config
            else None
        )
        logger.info(
            f"Created {self.identifier} with configs: {config}, "
            f"connection configs: {connection_config}"
        )

    def run(self) -> Generator[str, None, None]:
        for file_data in self.process.run():
            logger.debug(f"Generated file data: {file_data}")
            try:
                record_hash = self.get_hash(extras=[file_data.identifier])
                filename = f"{record_hash}.json"
                filepath = (self.cache_dir / filename).resolve()
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(str(filepath), "w") as f:
                    json.dump(file_data.to_dict(), f, indent=2)
                yield str(filepath)
            except Exception as e:
                logger.error(f"failed to create index for file data: {file_data}", exc_info=True)
                if self.context.raise_on_error:
                    raise e
                continue

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(self.process.index_config.to_dict())
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
