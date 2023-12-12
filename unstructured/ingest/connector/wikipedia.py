import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseSingleIngestDoc,
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
    page_title: str
    auto_suggest: bool = False


@dataclass
class WikipediaIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleWikipediaConfig = field(repr=False)

    @property
    @requires_dependencies(["wikipedia"], extras="wikipedia")
    def page(self) -> "WikipediaPage":
        import wikipedia

        return wikipedia.page(
            self.connector_config.page_title,
            auto_suggest=self.connector_config.auto_suggest,
        )

    def get_filename_prefix(self) -> str:
        title: str = str(self.connector_config.page_title)
        title = " ".join(title.split()).replace(" ", "-")
        return title

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
            "page_title": self.connector_config.page_title,
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
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        self.update_source_metadata()
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.text)


@dataclass
class WikipediaIngestHTMLDoc(WikipediaIngestDoc):
    registry_name: str = "wikipedia_html"

    @property
    def filename(self) -> Path:
        return (
            Path(self.read_config.download_dir) / f"{self.get_filename_prefix()}.html"
        ).resolve()

    @property
    def text(self):
        return self._get_html()

    @SourceConnectionNetworkError.wrap
    def _get_html(self):
        return self.page.html()

    @property
    def _output_filename(self):
        return Path(self.processor_config.output_dir) / f"{self.get_filename_prefix()}-html.json"


@dataclass
class WikipediaIngestTextDoc(WikipediaIngestDoc):
    registry_name: str = "wikipedia_text"

    @property
    def filename(self) -> Path:
        return (Path(self.read_config.download_dir) / f"{self.get_filename_prefix()}.txt").resolve()

    @property
    def text(self):
        return self._get_content()

    @SourceConnectionNetworkError.wrap
    def _get_content(self):
        return self.page.content

    @property
    def _output_filename(self):
        return Path(self.processor_config.output_dir) / f"{self.get_filename_prefix()}-txt.json"


@dataclass
class WikipediaIngestSummaryDoc(WikipediaIngestDoc):
    registry_name: str = "wikipedia_summary"

    @property
    def filename(self) -> Path:
        return (
            Path(self.read_config.download_dir) / f"{self.get_filename_prefix()}-summary.txt"
        ).resolve()

    @property
    def text(self):
        return self._get_summary()

    @SourceConnectionNetworkError.wrap
    def _get_summary(self):
        return self.page.summary

    @property
    def _output_filename(self):
        return Path(self.processor_config.output_dir) / f"{self.get_filename_prefix()}-summary.json"


@dataclass
class WikipediaSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleWikipediaConfig

    def initialize(self):
        pass

    @requires_dependencies(["wikipedia"], extras="wikipedia")
    def check_connection(self):
        import wikipedia

        try:
            wikipedia.page(
                self.connector_config.page_title,
                auto_suggest=self.connector_config.auto_suggest,
            )
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

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
