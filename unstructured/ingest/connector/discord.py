import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
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
    days: int
    token: str

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

    def __post_init__(self):
        pass

    @staticmethod
    def parse_channels(channel_str: str) -> List[str]:
        """Parses a comma separated list of channels into a list."""
        return [x.strip() for x in channel_str.split(",")]


@dataclass
class DiscordIngestDoc(BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).
    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleDiscordConfig
    channel: str
    days: int
    token: str

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

    @requires_dependencies(dependencies=["discord"], extras="discord")
    def get_file(self):
        """Actually fetches the data from discord and stores it locally."""

        import discord
        from discord.ext import commands

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
            logger.debug(f"fetching {self} - PID: {os.getpid()}")

        messages: List[discord.Message] = []

        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix=">", intents=intents)

        @bot.event
        async def on_ready():
            if self.days:
                after_date = dt.datetime.utcnow() - dt.timedelta(days=int(self.days))
            else:
                after_date = None

            channel = bot.get_channel(int(self.channel))
            async for msg in channel.history(after=after_date):  # type: ignore
                messages.append(msg)

            await bot.close()

        bot.run(self.token)

        with open(self._tmp_download_file(), "w") as f:
            for m in messages:
                f.write(m.content + "\n")

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        logger.info(f"Wrote {output_filename}")

    @property
    def filename(self):
        """The filename of the file created from a discord channel"""
        return self._tmp_download_file()

    def cleanup_file(self):
        """Removes the local copy the file after successful processing."""
        if not self.config.preserve_downloads:
            if self.config.verbose:
                logger.info(f"cleaning up channel {self.channel}")
            os.unlink(self._tmp_download_file())


class DiscordConnector(BaseConnector):
    """Objects of this class support fetching document(s) from"""

    def __init__(self, config: SimpleDiscordConfig):
        self.config = config
        self.cleanup_files = not config.preserve_downloads

    def cleanup(self, cur_dir=None):
        """cleanup linginering empty sub-dirs from s3 paths, but leave remaining files
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
        os.mkdir(self.config.download_dir)

    def get_ingest_docs(self):
        return [
            DiscordIngestDoc(
                self.config,
                channel,
                self.config.days,
                self.config.token,
            )
            for channel in self.config.channels
        ]
