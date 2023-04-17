import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    requires_dependencies,
    validate_date_args,
)

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


@dataclass
class SimpleSlackConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    channels: List[str]
    token: str
    oldest: str
    latest: str

    # Standard Connector options
    download_dir: str
    output_dir: str
    re_download: bool = False
    preserve_downloads: bool = False
    download_only: bool = False
    metadata_include: Optional[str] = None
    metadata_exclude: Optional[str] = None
    partition_by_api: bool = False
    partition_endpoint: str = "https://api.unstructured.io/general/v0/general"
    fields_include: str = "element_id,text,type,metadata"
    flatten_metadata: bool = False
    verbose: bool = False

    def validate_inputs(self):
        oldest_valid = True
        latest_valid = True

        if self.oldest:
            oldest_valid = validate_date_args(self.oldest)

        if self.latest:
            latest_valid = validate_date_args(self.latest)

        return oldest_valid, latest_valid

    def __post_init__(self):
        oldest_valid, latest_valid = self.validate_inputs()
        if not oldest_valid and not latest_valid:
            raise ValueError(
                "Start and/or End dates are not valid. ",
            )

    @staticmethod
    def parse_channels(channel_str: str) -> List[str]:
        """Parses a comma separated list of channels into a list."""
        return [x.strip() for x in channel_str.split(",")]


@dataclass
class SlackIngestDoc(BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleSlackConfig
    channel: str
    token: str
    oldest: str
    latest: str

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        channel_file = self.channel + ".txt"
        return Path(self.config.download_dir) / channel_file

    def _output_filename(self):
        output_file = self.channel + ".json"
        return Path(self.config.output_dir) / output_file

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and os.path.getsize(self._output_filename())

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(dependencies=["slack_sdk"], extras="slack")
    def get_file(self):
        """Fetches the data from a slack channel and stores it locally."""

        self._create_full_tmp_dir_path()
        if (
            not self.config.re_download
            and self._tmp_download_file().is_file()
            and os.path.getsize(self._tmp_download_file())
        ):
            if self.config.verbose:
                logger.debug(f"File exists: {self._tmp_download_file()}, skipping download")
            return

        if self.config.verbose:
            logger.debug(f"fetching channel {self.channel} - PID: {os.getpid()}")

        messages = []
        self.client = WebClient(token=self.token)

        try:
            oldest = "0"
            latest = "0"
            if self.oldest:
                oldest = self.convert_datetime(self.oldest)

            if self.latest:
                latest = self.convert_datetime(self.latest)

            result = self.client.conversations_history(
                channel=self.channel,
                oldest=oldest,
                latest=latest,
            )
            messages.extend(result["messages"])
            while result["has_more"]:
                result = self.client.conversations_history(
                    channel=self.channel,
                    oldest=oldest,
                    latest=latest,
                    cursor=result["response_metadata"]["next_cursor"],
                )
                messages.extend(result["messages"])
        except SlackApiError as e:
            logger.error(f"Error: {e}")

        with open(self._tmp_download_file(), "w") as channel_file:
            for message in messages:
                channel_file.write(message["text"] + "\n")

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")

    def convert_datetime(self, date_time):
        for format in DATE_FORMATS:
            try:
                return datetime.strptime(date_time, format).timestamp()
            except ValueError:
                pass

    @property
    def filename(self):
        """The filename of the file created from a slack channel"""
        return self._tmp_download_file()

    def cleanup_file(self):
        """Removes the local copy the file after successful processing."""
        if not self.config.preserve_downloads:
            if self.config.verbose:
                logger.info(f"cleaning up channel {self.channel}")
            os.unlink(self._tmp_download_file())


@requires_dependencies(dependencies=["slack_sdk"], extras="slack")
class SlackConnector(BaseConnector):
    """Objects of this class support fetching document(s) from"""

    def __init__(self, config: SimpleSlackConfig):
        self.config = config
        self.cleanup_files = not config.preserve_downloads

    def cleanup(self, cur_dir=None):
        """cleanup linginering empty sub-dirs, but leave remaining files
        (and their paths) in tact as that indicates they were not processed"""
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.config.download_dir
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
        """Verify that can get metadata for an object, validates connections info."""
        pass

    def get_ingest_docs(self):
        return [
            SlackIngestDoc(
                self.config,
                channel,
                self.config.token,
                self.config.oldest,
                self.config.latest,
            )
            for channel in self.config.channels
        ]
