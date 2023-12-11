import datetime as dt
import typing as t
from dataclasses import dataclass
from pathlib import Path

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError, SourceConnectionNetworkError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseSingleIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import (
    requires_dependencies,
)


@dataclass
class DiscordAccessConfig(AccessConfig):
    token: str = enhanced_field(sensitive=True)


@dataclass
class SimpleDiscordConfig(BaseConnectorConfig):
    """Connector config where channels is a comma separated list of
    Discord channels to pull messages from.
    """

    # Discord Specific Options
    access_config: DiscordAccessConfig
    channels: t.List[str]
    period: t.Optional[int] = None


@dataclass
class DiscordIngestDoc(IngestDocCleanupMixin, BaseSingleIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing!).
    Also includes a cleanup method. When things go wrong and the cleanup
    method is not called, the file is left behind on the filesystem to assist debugging.
    """

    connector_config: SimpleDiscordConfig
    channel: str
    days: t.Optional[int] = None
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
        return Path(self.processor_config.output_dir) / output_file

    def _create_full_tmp_dir_path(self):
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionNetworkError.wrap
    @requires_dependencies(dependencies=["discord"], extras="discord")
    def _get_messages(self):
        """Actually fetches the data from discord."""
        import discord
        from discord.ext import commands

        messages: t.List[discord.Message] = []
        jumpurl: t.List[str] = []
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
                jumpurl.append(channel.jump_url)  # type: ignore
                async for msg in channel.history(after=after_date):  # type: ignore
                    messages.append(msg)
                await bot.close()
            except Exception:
                logger.error("Error fetching messages")
                await bot.close()
                raise

        bot.run(self.connector_config.access_config.token)
        jump_url = None if len(jumpurl) < 1 else jumpurl[0]
        return messages, jump_url

    def update_source_metadata(self, **kwargs):
        messages, jump_url = kwargs.get("messages_tuple", self._get_messages())
        if messages == []:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        dates = [m.created_at for m in messages if m.created_at]
        dates.sort()
        self.source_metadata = SourceMetadata(
            date_created=dates[0].isoformat(),
            date_modified=dates[-1].isoformat(),
            source_url=jump_url,
            exists=True,
        )

    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        self._create_full_tmp_dir_path()

        messages, jump_url = self._get_messages()
        self.update_source_metadata(messages_tuple=(messages, jump_url))
        if messages == []:
            raise ValueError(f"Failed to retrieve messages from Discord channel {self.channel}")
        self._tmp_download_file().parent.mkdir(parents=True, exist_ok=True)
        with open(self._tmp_download_file(), "w") as f:
            for m in messages:
                f.write(m.content + "\n")

    @property
    def filename(self):
        """The filename of the file created from a discord channel"""
        return self._tmp_download_file()

    @property
    def version(self) -> t.Optional[str]:
        return None

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "channel": self.channel,
        }


class DiscordSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Objects of this class support fetching document(s) from"""

    connector_config: SimpleDiscordConfig

    def initialize(self):
        pass

    @requires_dependencies(dependencies=["discord"], extras="discord")
    def check_connection(self):
        import asyncio

        import discord
        from discord.client import Client

        intents = discord.Intents.default()
        try:
            client = Client(intents=intents)
            asyncio.run(client.start(token=self.connector_config.access_config.token))
        except Exception as e:
            logger.error(f"failed to validate connection: {e}", exc_info=True)
            raise SourceConnectionError(f"failed to validate connection: {e}")

    def get_ingest_docs(self):
        return [
            DiscordIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                channel=channel,
                days=self.connector_config.period,
            )
            for channel in self.connector_config.channels
        ]
