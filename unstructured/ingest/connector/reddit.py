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
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from praw.models import Submission


@dataclass
class SimpleRedditConfig(BaseConnectorConfig):
    subreddit_name: str
    client_id: t.Optional[str]
    client_secret: t.Optional[str]
    user_agent: str
    search_query: t.Optional[str]
    num_posts: int

    def __post_init__(self):
        if self.num_posts <= 0:
            raise ValueError("The number of Reddit posts to fetch must be positive.")


@dataclass
class RedditIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleRedditConfig = field(repr=False)
    post: "Submission"
    registry_name: str = "reddit"

    @property
    def filename(self) -> Path:
        return (Path(self.read_config.download_dir) / f"{self.post.id}.md").resolve()

    @property
    def _output_filename(self):
        return Path(self.partition_config.output_dir) / f"{self.post.id}.json"

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        # Write the title plus the body, if any
        text_to_write = f"# {self.post.title}\n{self.post.selftext}"
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(text_to_write)


@dataclass
class RedditSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleRedditConfig

    @requires_dependencies(["praw"], extras="reddit")
    def initialize(self):
        from praw import Reddit

        self.reddit = Reddit(
            client_id=self.connector_config.client_id,
            client_secret=self.connector_config.client_secret,
            user_agent=self.connector_config.user_agent,
        )

    def get_ingest_docs(self):
        subreddit = self.reddit.subreddit(self.connector_config.subreddit_name)
        if self.connector_config.search_query:
            posts = subreddit.search(
                self.connector_config.search_query,
                limit=self.connector_config.num_posts,
            )
        else:
            posts = subreddit.hot(limit=self.connector_config.num_posts)
        return [
            RedditIngestDoc(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                post=post,
            )
            for post in posts
        ]
