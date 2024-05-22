import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict
from unstructured.ingest.v2.processes.partitioner import Partitioner

STEP_ID = "partition"


class PartitionStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass
class PartitionStep(PipelineStep):
    process: Partitioner
    identifier: str = STEP_ID

    def __str__(self):
        return f"{self.identifier} ({self.process.config.strategy})"

    def __post_init__(self):
        config = sterilize_dict(self.process.config.to_dict(redact_sensitive=True))
        logger.info(f"Created {self.identifier} with configs: {config}")

    def should_partition(self, filepath: Path, file_data: FileData) -> bool:
        if self.context.reprocess or file_data.reprocess:
            return True
        if not filepath.exists():
            return True
        return False

    def get_output_filepath(self, filename: Path) -> Path:
        hashed_output_file = f"{self.get_hash(extras=[filename.stem])}.json"
        filepath = (self.cache_dir / hashed_output_file).resolve()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath

    def _save_output(self, output_filepath: str, partitioned_content: list[dict]):
        with open(str(output_filepath), "w") as f:
            logger.debug(f"Writing partitioned output to: {output_filepath}")
            json.dump(partitioned_content, f, indent=2)

    def _run(self, path: str, file_data_path: str) -> PartitionStepResponse:
        path = Path(path)
        file_data = FileData.from_file(path=file_data_path)
        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_partition(filepath=output_filepath, file_data=file_data):
            logger.debug(f"Skipping partitioning, output already exists: {output_filepath}")
            return PartitionStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        partitioned_content = self.process.run(filename=path, metadata=file_data.metadata)
        self._save_output(
            output_filepath=str(output_filepath), partitioned_content=partitioned_content
        )
        return PartitionStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    async def _run_async(self, path: str, file_data_path: str) -> PartitionStepResponse:
        path = Path(path)
        file_data = FileData.from_file(path=file_data_path)
        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_partition(filepath=output_filepath, file_data=file_data):
            logger.debug(f"Skipping partitioning, output already exists: {output_filepath}")
            return PartitionStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        if semaphore := self.context.semaphore:
            async with semaphore:
                partitioned_content = await self.process.run_async(
                    filename=path, metadata=file_data.metadata
                )
        else:
            partitioned_content = await self.process.run_async(
                filename=path, metadata=file_data.metadata
            )
        self._save_output(
            output_filepath=str(output_filepath), partitioned_content=partitioned_content
        )
        return PartitionStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(
            self.process.config.to_dict(), sort_keys=True, ensure_ascii=True
        )
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
