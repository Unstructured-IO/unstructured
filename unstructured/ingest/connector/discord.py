import datetime as dt
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
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
    channels: List[str]
    token: str
    days: Optional[int]
    verbose: bool = False

    def __post_init__(self):
        if self.days:
            try:
                self.days = int(self.days)
            except ValueError:
                raise ValueError("--discord-period must be an integer")

        pass

    @staticmethod
    def parse_channels(channel_str: str) -> List[str]:
        """Parses a comma separated list of channels into a list."""
        return [x.strip() for x in channel_str.split(",")]


@dataclass
class DiscordIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).
    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleDiscordConfig
    channel: str
    days: Optional[int]
    token: str

    def __post_init__(self):
        self.created_at = None
        self.latest_msg = None
        self.jump_url = None
        self.n_messages = 0

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        channel_file = self.channel + ".txt"
        return Path(self.standard_config.download_dir) / channel_file

    @property
    def _output_filename(self):
        output_file = self.channel + ".json"
        return Path(self.standard_config.output_dir) / output_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    @requires_dependencies(dependencies=["discord"], extras="discord")
    def get_file(self):
        """Actually fetches the data from discord and stores it locally."""

        import discord
        from discord.ext import commands

        self._create_full_tmp_dir_path()
        if self.config.verbose:
            logger.debug(f"fetching {self} - PID: {os.getpid()}")
        messages: List[discord.Message] = []
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
                if channel:
                    self.created_at = channel.created_at
                    self.jump_url = channel.jump_url
                async for msg in channel.history(after=after_date):  # type: ignore
                    messages.append(msg)
                await bot.close()
            except Exception as e:
                logger.error(f"Error fetching messages: {e}")
                await bot.close()

        bot.run(self.token)
        self.n_messages = len(messages)
        if self.n_messages >= 1:
            self.latest_msg = [m.created_at for m in messages if m.created_at].sort()

        with open(self._tmp_download_file(), "w") as f:
            for m in messages:
                f.write(m.content + "\n")

    @property
    def filename(self):
        """The filename of the file created from a discord channel"""
        return self._tmp_download_file()

    @property
    def date_created(self) -> Optional[str]:
        if self.created_at is not None:
            return self.created_at.isoformat()
        return self.created_at
        
    @property
    def date_modified(self) -> Optional[str]:
        if self.latest_msg is not None:
            return self.latest_msg.isoformat()
        return self.latest_msg

    @property
    def exists(self) -> Optional[bool]:
        return (self.n_messages >= 1)

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:
        return {
            "channel": self.channel,
            "jump_url": self.jump_url
        }


class DiscordConnector(ConnectorCleanupMixin, BaseConnector):
    """Objects of this class support fetching document(s) from"""

    config: SimpleDiscordConfig

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleDiscordConfig,
    ):
        super().__init__(standard_config, config)

    def initialize(self):
        """Verify that can get metadata for an object, validates connections info."""
        os.mkdir(self.standard_config.download_dir)

    def get_ingest_docs(self):
        return [
            DiscordIngestDoc(
                self.standard_config,
                self.config,
                channel,
                self.config.days,
                self.config.token,
            )
            for channel in self.config.channels
        ]
