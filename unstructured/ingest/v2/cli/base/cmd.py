from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Optional, Type

import click

from unstructured.ingest.v2.cli.configs.chunk import ChunkerCliConfig
from unstructured.ingest.v2.cli.configs.partition import PartitionerCliConfig
from unstructured.ingest.v2.cli.interfaces import CliConfig
from unstructured.ingest.v2.cli.utils import extract_config
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.chunker import Chunker
from unstructured.ingest.v2.processes.connector_registry import (
    DownloaderT,
    IndexerT,
    UploaderT,
    UploadStagerT,
    destination_registry,
    source_registry,
)
from unstructured.ingest.v2.processes.partitioner import Partitioner


@dataclass
class BaseCmd(ABC):
    cmd_name: str
    default_configs: list[Type[CliConfig]] = field(default_factory=list)

    @property
    def cmd_name_key(self):
        return self.cmd_name.replace("-", "_")

    def add_options(self, cmd: click.Command, extras: list[Type[CliConfig]]) -> click.Command:
        configs = self.default_configs
        # make sure what's unique to this cmd appears first
        extras.extend(configs)
        for config in extras:
            try:
                config.add_cli_options(cmd=cmd)
            except ValueError as e:
                raise ValueError(f"failed to set configs from {config.__name__}: {e}")
        return cmd

    def get_pipline(
        self,
        src: str,
        source_options: dict[str, Any],
        dest: Optional[str] = None,
        destination_options: Optional[dict[str, Any]] = None,
    ) -> Pipeline:
        pass

    @staticmethod
    def get_chunker(options: dict[str, Any]) -> Optional[Chunker]:
        chunker_config = ChunkerCliConfig.from_flat_dict(flat_data=options)
        if not chunker_config.chunking_strategy:
            return None
        return Chunker(config=chunker_config)

    @staticmethod
    def get_partitioner(options: dict[str, Any]) -> Partitioner:
        partitioner_config = PartitionerCliConfig.from_flat_dict(flat_data=options)
        return Partitioner(config=partitioner_config)

    @staticmethod
    def get_indexer(src: str, options: dict[str, Any]) -> IndexerT:
        source_entry = source_registry[src]
        indexer_config = None
        if indexer_config_cls := source_entry.indexer_config:
            indexer_config = extract_config(flat_data=options, config=indexer_config_cls)
        indexer_cls = source_entry.indexer
        return indexer_cls(config=indexer_config)

    @staticmethod
    def get_downloader(src: str, options: dict[str, Any]) -> DownloaderT:
        source_entry = source_registry[src]
        downloader_config = None
        if downloader_config_cls := source_entry.downloader_config:
            downloader_config = extract_config(flat_data=options, config=downloader_config_cls)
        connection_config = None
        if connection_config_cls := source_entry.connection_config:
            connection_config = extract_config(flat_data=options, config=connection_config_cls)
        downloader_cls = source_entry.downloader
        return downloader_cls(config=downloader_config, connection_config=connection_config)

    @staticmethod
    def get_upload_stager(dest: str, options: dict[str, Any]) -> Optional[UploadStagerT]:
        dest_entry = destination_registry[dest]
        upload_stager_config = None
        if upload_stager_config_cls := dest_entry.upload_stager_config:
            upload_stager_config = extract_config(
                flat_data=options, config=upload_stager_config_cls
            )
        if upload_stager_cls := dest_entry.upload_stager:
            return upload_stager_cls(config=upload_stager_config)
        return None

    @staticmethod
    def get_uploader(dest, options: dict[str, Any]) -> UploaderT:
        dest_entry = destination_registry[dest]
        uploader_config = None
        if uploader_config_cls := dest_entry.uploader_config:
            uploader_config = extract_config(flat_data=options, config=uploader_config_cls)
        connection_config = None
        if connection_config_cls := dest_entry.connection_config:
            connection_config = extract_config(flat_data=options, config=connection_config_cls)
        uploader_cls = dest_entry.uploader
        return uploader_cls(config=uploader_config, connection_config=connection_config)
