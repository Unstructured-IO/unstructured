import os
import typing as t
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from wikipedia import WikipediaPage


@dataclass
class SimpleWikipediaConfig(BaseConnectorConfig):
    title: str
    auto_suggest: bool


@dataclass
class WikipediaFileMeta:
    version: t.Optional[str] = None
    source_url: t.Optional[str] = None
    exists: t.Optional[bool] = None


@dataclass
class WikipediaIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleWikipediaConfig = field(repr=False)

    @property
    @requires_dependencies(["wikipedia"], extras="wikipedia")
    def page(self) -> "WikipediaPage":
        import wikipedia

        return wikipedia.page(
            self.connector_config.title,
            auto_suggest=self.connector_config.auto_suggest,
        )

    @cached_property
    @requires_dependencies(["wikipedia"], extras="wikipedia")
    def file_metadata(self):
        import wikipedia
        from wikipedia.exceptions import PageError

        try:
            page = wikipedia.page(
                self.connector_config.title,
                auto_suggest=self.connector_config.auto_suggest,
            )
        except PageError:
            return WikipediaFileMeta(
                exists=False,
            )
        return WikipediaFileMeta(
            page.revision_id,
            page.url,
            True,
        )

    @property
    def filename(self) -> Path:
        raise NotImplementedError()

    @property
    def text(self) -> str:
        raise NotImplementedError()

    @property
    def _output_filename(self):
        raise NotImplementedError()

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.text)

    @property
    def exists(self) -> t.Optional[bool]:
        return self.file_metadata.exists

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "page_title": self.connector_config.title,
            "page_url": self.file_metadata.source_url,
        }

    @property
    def version(self) -> t.Optional[str]:
        return self.file_metadata.version

    @property
    def source_url(self) -> t.Optional[str]:
        return self.file_metadata.source_url


@dataclass
class WikipediaIngestHTMLDoc(WikipediaIngestDoc):
    registry_name: str = "wikipedia_html"

    @property
    def filename(self) -> Path:
        return (
            Path(self.read_config.download_dir) / f"{self.page.title}-{self.page.revision_id}.html"
        ).resolve()

    @property
    def text(self):
        return self.page.html()

    @property
    def _output_filename(self):
        return (
            Path(self.partition_config.output_dir)
            / f"{self.page.title}-{self.page.revision_id}-html.json"
        )


@dataclass
class WikipediaIngestTextDoc(WikipediaIngestDoc):
    registry_name: str = "wikipedia_text"

    @property
    def filename(self) -> Path:
        return (
            Path(self.read_config.download_dir) / f"{self.page.title}-{self.page.revision_id}.txt"
        ).resolve()

    @property
    def text(self):
        return self.page.content

    @property
    def _output_filename(self):
        return (
            Path(self.partition_config.output_dir)
            / f"{self.page.title}-{self.page.revision_id}-txt.json"
        )


@dataclass
class WikipediaIngestSummaryDoc(WikipediaIngestDoc):
    registry_name: str = "wikipedia_summary"

    @property
    def filename(self) -> Path:
        return (
            Path(self.read_config.download_dir)
            / f"{self.page.title}-{self.page.revision_id}-summary.txt"
        ).resolve()

    @property
    def text(self):
        return self.page.summary

    @property
    def _output_filename(self):
        return (
            Path(self.partition_config.output_dir)
            / f"{self.page.title}-{self.page.revision_id}-summary.json"
        )


@dataclass
class WikipediaSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleWikipediaConfig

    def initialize(self):
        pass

    def get_ingest_docs(self):
        return [
            WikipediaIngestTextDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
            ),
            WikipediaIngestHTMLDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
            ),
            WikipediaIngestSummaryDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
            ),
        ]
