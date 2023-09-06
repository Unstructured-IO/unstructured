import os
import typing as t
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
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
from unstructured.utils import (
    requires_dependencies,
    validate_date_args,
)

DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")


@dataclass
class SimpleSlackConfig(BaseConnectorConfig):
    """Connector config to process all messages by channel id's."""

    channels: t.List[str]
    token: str
    oldest: t.Optional[str]
    latest: t.Optional[str]
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


@dataclass
class SlackIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).

    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    connector_config: SimpleSlackConfig
    channel: str
    token: str
    oldest: t.Optional[str]
    latest: t.Optional[str]
    registry_name: str = "slack"

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        channel_file = self.channel + ".xml"
        return Path(self.read_config.download_dir) / channel_file

    @property
    def _output_filename(self):
        output_file = self.channel + ".json"
        return Path(self.partition_config.output_dir) / output_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["slack_sdk"], extras="slack")
    def get_file(self):
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError

        """Fetches the data from a slack channel and stores it locally."""

        self._create_full_tmp_dir_path()

        if self.connector_config.verbose:
            logger.debug(f"fetching channel {self.channel} - PID: {os.getpid()}")

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

            root = ET.Element("messages")
            for message in result["messages"]:
                message_elem = ET.SubElement(root, "message")
                text_elem = ET.SubElement(message_elem, "text")
                text_elem.text = message.get("text")

                cursor = None
                while True:
                    try:
                        response = self.client.conversations_replies(
                            channel=self.channel,
                            ts=message["ts"],
                            cursor=cursor,
                        )

                        for reply in response["messages"]:
                            reply_msg = reply.get("text")
                            text_elem.text = "".join([str(text_elem.text), " <reply> ", reply_msg])

                        if not response["has_more"]:
                            break

                        cursor = response["response_metadata"]["next_cursor"]

                    except SlackApiError as e:
                        print(f"Error retrieving replies: {e.response['error']}")

        except SlackApiError as e:
            logger.error(f"Error: {e}")

        tree = ET.ElementTree(root)
        tree.write(self._tmp_download_file(), encoding="utf-8", xml_declaration=True)

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


@requires_dependencies(dependencies=["slack_sdk"], extras="slack")
class SlackSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleSlackConfig

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        pass

    def get_ingest_docs(self):
        return [
            SlackIngestDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                channel=channel,
                token=self.connector_config.token,
                oldest=self.connector_config.oldest,
                latest=self.connector_config.latest,
            )
            for channel in self.connector_config.channels
        ]
