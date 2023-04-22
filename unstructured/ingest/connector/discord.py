from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import List

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

@dataclass
class SimpleDiscordConfig(BaseConnectorConfig):
    """Connector config where s3_url is an s3 prefix to process all documents from."""

    # Discord Specific Options
    channels: List[str]
    days: int

    # Standard Connector options
    download_dir: str
    output_dir: str
    re_download: bool = False
    preserve_downloads: bool = False
    verbose: bool = False

    def __post_init__(self):
        pass

    @staticmethod    
    def parse_channels(channel_str: str) -> List[str]:
        """Parses a comma separated list of channels into a list.
        """
        [x.strip() for x in channel_str.split(",")]



@dataclass
class DiscordIngestDoc(BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).
    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    config: SimpleDiscordConfig
    channel: str
    api_token: str

    # NOTE(crag): probably doesn't matter,  but intentionally not defining tmp_download_file
    # __post_init__ for multiprocessing simplicity (no Path objects in initially
    # instantiated object)
    def _tmp_download_file(self):
        return Path(self.config.download_dir) / self.channel

    def _output_filename(self):
        return Path(self.config.output_dir) / self.channel

    def has_output(self):
        """Determine if structured output for this doc already exists."""
        return self._output_filename().is_file() and os.path.getsize(self._output_filename())

    def _create_full_tmp_dir_path(self):
        """includes "directories" in s3 object path"""
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(dependencies=["discord.py"], extras="discord")
    def get_file(self):
        """Actually fetches the data from discord and stores it locally."""
        import discord
        import asyncio

        self._create_full_tmp_dir_path()
        if (
            not self.config.re_download
            and self._tmp_download_file().is_file()
            and os.path.getsize(self._tmp_download_file())
        ):
            if self.config.verbose:
                print(f"File exists: {self._tmp_download_file()}, skipping download")
            return

        if self.config.verbose:
            print(f"fetching {self} - PID: {os.getpid()}")

        channel_id = self.channel
        messages: List[discord.Message] = []

        class Client(discord.Client):
            async def on_ready(self) -> None:
                try:
                    channel = client.get_channel()
                    if not isinstance(channel, discord.TextChannel):
                        raise ValueError(
                            f"Channel {channel_id} is not a text channel. "
                            "Only text channels are supported for now."
                        )

                    async for msg in channel.history():
                        messages.append(msg)                        
                finally:
                    await self.close()

        intents = discord.Intents.default()
        intents.message_content = True
        client = Client(intents=intents)
        asyncio.run_until_complete(client.start(self.api_token))

        with open(self._tmp_download_file(), 'w') as f:
            for m in messages:
                f.write(m.content + "\n")        

    def write_result(self):
        """Write the structured json result for this doc. result must be json serializable."""
        output_filename = self._output_filename()
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w") as output_f:
            output_f.write(json.dumps(self.isd_elems_no_filename, ensure_ascii=False, indent=2))
        print(f"Wrote {output_filename}")

    @property
    def filename(self):
        """The filename of the file after downloading from s3"""
        return self._tmp_download_file()

    def cleanup_file(self):
        """Removes the local copy the file after successful processing."""
        if not self.config.preserve_downloads:
            if self.config.verbose:
                print(f"cleaning up {self}")
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
            )
            for channel in self.config.channels
        ]