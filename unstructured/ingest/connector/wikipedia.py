import os
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
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

    @property
    def filename(self) -> Path:
        raise NotImplementedError()

    @property
    def text(self) -> str:
        raise NotImplementedError()

    @property
    def _output_filename(self):
        raise NotImplementedError()

    @property
    def date_created(self) -> t.Optional[str]:
        return None

    @property
    def date_modified(self) -> t.Optional[str]:
        return None

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "page_title": self.connector_config.title,
            "page_url": self.source_metadata.source_url,  # type: ignore
        }

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(["wikipedia"], extras="wikipedia")
    def update_source_metadata(self):
        from wikipedia.exceptions import PageError

        try:
            page = self.page
        except PageError:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return

        self.source_metadata = SourceMetadata(
            version=page.revision_id,
            source_url=page.url,
            exists=True,
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        self.update_source_metadata()
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.text)


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
            Path(self.processor_config.output_dir)
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
            Path(self.processor_config.output_dir)
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
            Path(self.processor_config.output_dir)
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
                processor_config=self.processor_config,
                connector_config=self.connector_config,
                read_config=self.read_config,
            ),
            WikipediaIngestHTMLDoc(
                processor_config=self.processor_config,
                connector_config=self.connector_config,
                read_config=self.read_config,
            ),
            WikipediaIngestSummaryDoc(
                processor_config=self.processor_config,
                connector_config=self.connector_config,
                read_config=self.read_config,
            ),
        ]
