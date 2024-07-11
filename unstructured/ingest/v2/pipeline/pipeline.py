import logging
import multiprocessing as mp
from dataclasses import InitVar, dataclass, field
from time import time
from typing import Any, Optional, Union

from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.logger import logger, make_default_logger
from unstructured.ingest.v2.pipeline.steps.chunk import Chunker, ChunkStep
from unstructured.ingest.v2.pipeline.steps.download import DownloaderT, DownloadStep
from unstructured.ingest.v2.pipeline.steps.embed import Embedder, EmbedStep
from unstructured.ingest.v2.pipeline.steps.index import IndexerT, IndexStep
from unstructured.ingest.v2.pipeline.steps.partition import Partitioner, PartitionStep
from unstructured.ingest.v2.pipeline.steps.stage import UploadStager, UploadStageStep
from unstructured.ingest.v2.pipeline.steps.uncompress import Uncompressor, UncompressStep
from unstructured.ingest.v2.pipeline.steps.upload import Uploader, UploadStep
from unstructured.ingest.v2.pipeline.utils import sterilize_dict
from unstructured.ingest.v2.processes.chunker import ChunkerConfig
from unstructured.ingest.v2.processes.connector_registry import (
    ConnectionConfig,
    DownloaderConfigT,
    IndexerConfigT,
    UploaderConfigT,
    UploadStagerConfigT,
    destination_registry,
    source_registry,
)
from unstructured.ingest.v2.processes.connectors.local import LocalUploader
from unstructured.ingest.v2.processes.embedder import EmbedderConfig
from unstructured.ingest.v2.processes.partitioner import PartitionerConfig


class PipelineError(Exception):
    pass


@dataclass
class Pipeline:
    context: ProcessorConfig
    indexer: InitVar[IndexerT]
    indexer_step: IndexStep = field(init=False)
    downloader: InitVar[DownloaderT]
    downloader_step: DownloadStep = field(init=False)
    partitioner: InitVar[Partitioner]
    partitioner_step: PartitionStep = field(init=False)
    chunker: InitVar[Optional[Chunker]] = None
    chunker_step: ChunkStep = field(init=False, default=None)
    embedder: InitVar[Optional[Embedder]] = None
    embedder_step: EmbedStep = field(init=False, default=None)
    stager: InitVar[Optional[UploadStager]] = None
    stager_step: UploadStageStep = field(init=False, default=None)
    uploader: InitVar[Uploader] = field(default=LocalUploader())
    uploader_step: UploadStep = field(init=False, default=None)
    uncompress_step: UncompressStep = field(init=False, default=None)

    def __post_init__(
        self,
        indexer: IndexerT,
        downloader: DownloaderT,
        partitioner: Partitioner,
        chunker: Chunker = None,
        embedder: Embedder = None,
        stager: UploadStager = None,
        uploader: Uploader = None,
    ):
        make_default_logger(level=logging.DEBUG if self.context.verbose else logging.INFO)
        self.indexer_step = IndexStep(process=indexer, context=self.context)
        self.downloader_step = DownloadStep(process=downloader, context=self.context)
        self.partitioner_step = PartitionStep(process=partitioner, context=self.context)
        self.chunker_step = ChunkStep(process=chunker, context=self.context) if chunker else None

        self.embedder_step = EmbedStep(process=embedder, context=self.context) if embedder else None
        # TODO: support initialize() call from each step process
        # Potential long call to download embedder models, run before any fanout:
        if embedder and embedder.config:
            embedder.config.get_embedder().initialize()

        self.stager_step = UploadStageStep(process=stager, context=self.context) if stager else None
        self.uploader_step = UploadStep(process=uploader, context=self.context)
        if self.context.uncompress:
            process = Uncompressor()
            self.uncompress_step = UncompressStep(process=process, context=self.context)

        self.check_destination_connector()

    def check_destination_connector(self):
        # Make sure that if the set destination connector expects a stager, one is also set
        if not self.uploader_step:
            return
        uploader_connector_type = self.uploader_step.process.connector_type
        registry_entry = destination_registry[uploader_connector_type]
        if registry_entry.upload_stager and self.stager_step is None:
            raise ValueError(
                f"pipeline with uploader type {self.uploader_step.process.__class__.__name__} "
                f"expects a stager of type {registry_entry.upload_stager.__name__} "
                f"but one was not set"
            )

    def cleanup(self):
        pass

    def log_statuses(self):
        if status := self.context.status:
            logger.error(f"{len(status)} failed documents:")
            for k, v in status.items():
                for kk, vv in v.items():
                    logger.error(f"{k}: [{kk}] {vv}")

    def run(self):
        try:
            start_time = time()
            self._run()
            logger.info(f"Finished ingest process in {time() - start_time}s")
        finally:
            self.log_statuses()
            self.cleanup()
            if self.context.status:
                raise PipelineError("Pipeline did not run successfully")

    def clean_results(self, results: Optional[list[Union[Any, list[Any]]]]) -> Optional[list[Any]]:
        if not results:
            return None
        results = [r for r in results if r]
        flat = []
        for r in results:
            if isinstance(r, list):
                flat.extend(r)
            else:
                flat.append(r)
        final = [f for f in flat if f]
        return final or None

    def _run(self):
        logger.info(
            f"Running local pipline: {self} with configs: "
            f"{sterilize_dict(self.context.to_dict(redact_sensitive=True))}"
        )
        if self.context.mp_supported:
            manager = mp.Manager()
            self.context.status = manager.dict()
        else:
            self.context.status = {}

        # Index into data source
        indices = self.indexer_step.run()
        indices_inputs = [{"file_data_path": i} for i in indices]
        if not indices_inputs:
            return

        # Download associated content to local file system
        downloaded_data = self.downloader_step(indices_inputs)
        downloaded_data = self.clean_results(results=downloaded_data)
        if not downloaded_data:
            return

        # Run uncompress if available
        if self.uncompress_step:
            downloaded_data = self.uncompress_step(downloaded_data)
            # Flatten list of lists
            downloaded_data = self.clean_results(results=downloaded_data)

        if not downloaded_data:
            return

        # Partition content
        elements = self.partitioner_step(downloaded_data)
        elements = self.clean_results(results=elements)
        if not elements:
            return

        # Run element specific modifiers
        for step in [self.chunker_step, self.embedder_step, self.stager_step]:
            elements = step(elements) if step else elements
            elements = self.clean_results(results=elements)
            if not elements:
                return

        # Upload the final result
        self.uploader_step(iterable=elements)

    def __str__(self):
        s = [str(self.indexer_step), str(self.downloader_step)]
        if uncompress_step := self.uncompress_step:
            s.append(str(uncompress_step))
        s.append(str(self.partitioner_step))
        if chunker_step := self.chunker_step:
            s.append(str(chunker_step))
        if embedder_step := self.embedder_step:
            s.append(str(embedder_step))
        if stager_step := self.stager_step:
            s.append(str(stager_step))
        s.append(str(self.uploader_step))
        return " -> ".join(s)

    @classmethod
    def from_configs(
        cls,
        context: ProcessorConfig,
        indexer_config: IndexerConfigT,
        downloader_config: DownloaderConfigT,
        source_connection_config: ConnectionConfig,
        partitioner_config: PartitionerConfig,
        chunker_config: Optional[ChunkerConfig] = None,
        embedder_config: Optional[EmbedderConfig] = None,
        destination_connection_config: Optional[ConnectionConfig] = None,
        stager_config: Optional[UploadStagerConfigT] = None,
        uploader_config: Optional[UploaderConfigT] = None,
    ) -> "Pipeline":
        # Get registry key based on indexer config
        source_entry = {
            k: v
            for k, v in source_registry.items()
            if isinstance(indexer_config, v.indexer_config)
            and isinstance(downloader_config, v.downloader_config)
            and isinstance(source_connection_config, v.connection_config)
        }
        if len(source_entry) > 1:
            raise ValueError(
                f"multiple entries found matching provided indexer, "
                f"downloader and connection configs: {source_entry}"
            )
        if len(source_entry) != 1:
            raise ValueError(
                "no entry found in source registry with matching indexer, "
                "downloader and connection configs"
            )
        source = list(source_entry.values())[0]
        pipeline_kwargs = {
            "context": context,
            "indexer": source.indexer(
                index_config=indexer_config, connection_config=source_connection_config
            ),
            "downloader": source.downloader(
                download_config=downloader_config, connection_config=source_connection_config
            ),
            "partitioner": Partitioner(config=partitioner_config),
        }
        if chunker_config:
            pipeline_kwargs["chunker"] = Chunker(config=chunker_config)
        if embedder_config:
            pipeline_kwargs["embedder"] = Embedder(config=embedder_config)
        if not uploader_config:
            return Pipeline(**pipeline_kwargs)

        destination_entry = {
            k: v
            for k, v in destination_registry.items()
            if isinstance(uploader_config, v.uploader_config)
        }
        if destination_connection_config:
            destination_entry = {
                k: v
                for k, v in destination_entry.items()
                if isinstance(destination_connection_config, v.connection_config)
            }
        if stager_config:
            destination_entry = {
                k: v
                for k, v in destination_entry.items()
                if isinstance(stager_config, v.upload_stager_config)
            }

        if len(destination_entry) > 1:
            raise ValueError(
                f"multiple entries found matching provided uploader, "
                f"stager and connection configs: {destination_entry}"
            )
        if len(destination_entry) != 1:
            raise ValueError(
                "no entry found in source registry with matching uploader, "
                "stager and connection configs"
            )

        destination = list(destination_entry.values())[0]
        if stager_config:
            pipeline_kwargs["stager"] = destination.upload_stager(
                upload_stager_config=stager_config
            )
        if uploader_config:
            uploader_kwargs = {"upload_config": uploader_config}
            if destination_connection_config:
                uploader_kwargs["connection_config"] = destination_connection_config
            pipeline_kwargs["uploader"] = destination.uploader(**uploader_kwargs)
        return cls(**pipeline_kwargs)
