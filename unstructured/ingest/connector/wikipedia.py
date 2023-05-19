import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger

if TYPE_CHECKING:
    from wikipedia import WikipediaPage


@dataclass
class SimpleWikipediaConfig(BaseConnectorConfig):
    title: str
    auto_suggest: bool


@dataclass
class WikipediaIngestDoc(BaseIngestDoc):
    config: SimpleWikipediaConfig = field(repr=False)
    page: "WikipediaPage"

    @property
    def filename(self) -> Path:
        raise NotImplementedError()

    @property
    def text(self) -> str:
        raise NotImplementedError()

    def _output_filename(self):
        raise NotImplementedError()

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    def cleanup_file(self):
        """Removes the local copy of the file (or anything else) after successful processing."""
        if not self.standard_config.preserve_downloads and not self.standard_config.download_only:
            logger.debug(f"Cleaning up {self}")
            os.unlink(self.filename)

    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        if (
            not self.standard_config.re_download
            and self.filename.is_file()
            and self.filename.stat()
        ):
            logger.debug(f"File exists: {self.filename}, skipping download")
            return

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.text)

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        output_filename = self._output_filename()
        return output_filename.is_file() and output_filename.stat()

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        if self.standard_config.download_only:
            return
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w", encoding="utf8") as output_f:
            json.dump(self.isd_elems_no_filename, output_f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote {output_filename}")


class WikipediaIngestHTMLDoc(WikipediaIngestDoc):
    @property
    def filename(self) -> Path:
        return (
            Path(self.standard_config.download_dir)
            / f"{self.page.title}-{self.page.revision_id}.html"
        ).resolve()

    @property
    def text(self):
        return self.page.html()

    def _output_filename(self):
        return (
            Path(self.standard_config.output_dir)
            / f"{self.page.title}-{self.page.revision_id}-html.json"
        )


class WikipediaIngestTextDoc(WikipediaIngestDoc):
    @property
    def filename(self) -> Path:
        return (
            Path(self.standard_config.download_dir)
            / f"{self.page.title}-{self.page.revision_id}.txt"
        ).resolve()

    @property
    def text(self):
        return self.page.content

    def _output_filename(self):
        return (
            Path(self.standard_config.output_dir)
            / f"{self.page.title}-{self.page.revision_id}-txt.json"
        )


class WikipediaIngestSummaryDoc(WikipediaIngestDoc):
    @property
    def filename(self) -> Path:
        return (
            Path(self.standard_config.download_dir)
            / f"{self.page.title}-{self.page.revision_id}-summary.txt"
        ).resolve()

    @property
    def text(self):
        return self.page.summary

    def _output_filename(self):
        return (
            Path(self.standard_config.output_dir)
            / f"{self.page.title}-{self.page.revision_id}-summary.json"
        )


class WikipediaConnector(BaseConnector):
    config: SimpleWikipediaConfig

    def __init__(self, config: SimpleWikipediaConfig, standard_config: StandardConnectorConfig):
        super().__init__(standard_config, config)
        self.cleanup_files = (
            not standard_config.preserve_downloads and not standard_config.download_only
        )

    def cleanup(self, cur_dir=None):
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.standard_config.download_dir
        sub_dirs = os.listdir(cur_dir)
        os.chdir(cur_dir)
        for sub_dir in sub_dirs:
            # don't traverse symlinks, not that there every should be any
            if os.path.isdir(sub_dir) and not os.path.islink(sub_dir):
                self.cleanup(sub_dir)
        os.chdir("..")
        if len(os.listdir(cur_dir)) == 0:
            os.rmdir(cur_dir)

    def initialize(self):
        pass

    def get_ingest_docs(self):
        import wikipedia

        page = wikipedia.page(
            self.config.title,
            auto_suggest=self.config.auto_suggest,
        )
        return [
            WikipediaIngestTextDoc(self.standard_config, self.config, page),
            WikipediaIngestHTMLDoc(self.standard_config, self.config, page),
            WikipediaIngestSummaryDoc(self.standard_config, self.config, page),
        ]
