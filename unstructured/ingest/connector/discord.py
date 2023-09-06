import datetime as dt
import os
import typing as t
from dataclasses import dataclass
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
)


@dataclass
class SimpleDiscordConfig(BaseConnectorConfig):
    """Connector config where channels is a comma separated list of
    Discord channels to pull messages from.
    """

    # Discord Specific Options
    channels: t.List[str]
    token: str
    days: t.Optional[int]
    verbose: bool = False

    def __post_init__(self):
        if self.days:
            try:
                self.days = int(self.days)
            except ValueError:
                raise ValueError("--discord-period must be an integer")

        pass


@dataclass
class DiscordIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).
    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    connector_config: SimpleDiscordConfig
    channel: str
    days: t.Optional[int]
    token: str
    registry_name: str = "discord"

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        channel_file = self.channel + ".txt"
        return Path(self.read_config.download_dir) / channel_file

    @property
    def _output_filename(self):
        output_file = self.channel + ".json"
        return Path(self.partition_config.output_dir) / output_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["discord"], extras="discord")
    def get_file(self):
        """Actually fetches the data from discord and stores it locally."""

        import discord
        from discord.ext import commands

        self._create_full_tmp_dir_path()
        if self.connector_config.verbose:
            logger.debug(f"fetching {self} - PID: {os.getpid()}")
        messages: t.List[discord.Message] = []
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix=">", intents=intents)

        @bot.event
        async def on_ready():
            try:
                after_date = None
                if self.days:
                    after_date = dt.datetime.utcnow() - dt.timedelta(days=self.days)

                channel = bot.get_channel(int(self.channel))
                async for msg in channel.history(after=after_date):  # type: ignore
                    messages.append(msg)

                await bot.close()
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                await bot.close()

        bot.run(self.token)

        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)
        with open(self._tmp_download_file(), "w") as f:
            for m in messages:
                f.write(m.content + "\n")

    @property
    def filename(self):
        """The filename of the file created from a discord channel"""
        return self._tmp_download_file()


class DiscordSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleDiscordConfig

    def initialize(self):
        pass

    def get_ingest_docs(self):
        return [
            DiscordIngestDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                channel=channel,
                days=self.connector_config.days,
                token=self.connector_config.token,
            )
            for channel in self.connector_config.channels
        ]
