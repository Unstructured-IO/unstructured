import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

from unstructured.ingest.v2.interfaces import FileData
from unstructured.ingest.v2.logger import logger
from unstructured.ingest.v2.pipeline.interfaces import PipelineStep, log_error
from unstructured.ingest.v2.processes.embedder import Embedder
from unstructured.staging.base import elements_to_dicts

STEP_ID = "embed"


class EmbedStepResponse(TypedDict):
    file_data_path: str
    path: str


@dataclass(kw_only=True)
class EmbedStep(PipelineStep):
    identifier: str = STEP_ID
    process: Embedder

    def should_embed(self, filepath: Path, file_data: FileData) -> bool:
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

    def _save_output(self, output_filepath: str, embedded_content: list[dict]):
        with open(str(output_filepath), "w") as f:
            logger.debug(f"Writing embedded output to: {output_filepath}")
            json.dump(embedded_content, f, indent=2)

    @log_error()
    def run(self, path: str, file_data_path: str) -> EmbedStepResponse:
        path = Path(path)
        file_data = FileData.from_file(path=file_data_path)

        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_embed(filepath=output_filepath, file_data=file_data):
            logger.info(f"Skipping embedding, output already exists: {output_filepath}")
            return EmbedStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        embed_content_raw = self.process.run(elements_filepath=path)
        self._save_output(
            output_filepath=str(output_filepath),
            embedded_content=elements_to_dicts(embed_content_raw),
        )
        return EmbedStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    async def run_async(self, path: str, file_data_path: str) -> EmbedStepResponse:
        path = Path(path)
        file_data = FileData.from_file(path=file_data_path)
        output_filepath = self.get_output_filepath(filename=path)
        if not self.should_embed(filepath=output_filepath, file_data=file_data):
            logger.info(f"Skipping embedding, output already exists: {output_filepath}")
            return EmbedStepResponse(file_data_path=file_data_path, path=str(output_filepath))
        embed_content_raw = await self.process.run_async(elements_filepath=path)
        self._save_output(
            output_filepath=str(output_filepath),
            embedded_content=elements_to_dicts(embed_content_raw),
        )
        return EmbedStepResponse(file_data_path=file_data_path, path=str(output_filepath))

    def get_hash(self, extras: Optional[list[str]]) -> str:
        hashable_string = json.dumps(
            self.process.config.to_dict(), sort_keys=True, ensure_ascii=True
        )
        if extras:
            hashable_string += "".join(extras)
        return hashlib.sha256(hashable_string.encode()).hexdigest()[:12]
