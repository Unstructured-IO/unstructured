import os
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSourceConnector,
    IngestDocCleanupMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


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
    post_id: str
    registry_name: str = "reddit"

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(["praw"])
    def get_post(self):
        from praw import Reddit
        from praw.models import Submission

        try:
            reddit = Reddit(
                client_id=self.connector_config.client_id,
                client_secret=self.connector_config.client_secret,
                user_agent=self.connector_config.user_agent,
            )
            post = Submission(reddit, self.post_id)
        except Exception:
            logger.error(f"Failed to retrieve post with id {self.post_id}")
            return None
        return post

    def update_source_metadata(self, **kwargs):
        post = kwargs.get("post", self.get_post())
        if post is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return

        file_exists = (post.author != "[deleted]" or post.auth is not None) and (
            post.selftext != "[deleted]" or post.selftext != "[removed]"
        )

        self.source_metadata = SourceMetadata(
            date_created=datetime.utcfromtimestamp(post.created_utc).isoformat(),
            source_url=post.permalink,
            exists=file_exists,
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        # Write the title plus the body, if any
        post = self.get_post()
        self.update_source_metadata(post=post)
        if post is None:
            raise ValueError(
                f"Failed to retrieve post {self.post_id}",
            )

        text_to_write = f"# {post.title}\n{post.selftext}"
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(text_to_write)

    @property
    def filename(self) -> Path:
        return (Path(self.read_config.download_dir) / f"{self.post_id}.md").resolve()

    @property
    def _output_filename(self):
        return Path(self.processor_config.output_dir) / f"{self.post_id}.json"

    @property
    def date_modified(self) -> t.Optional[str]:
        return None

    @property
    def version(self) -> t.Optional[str]:
        return None


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
                processor_config=self.processor_config,
                read_config=self.read_config,
                post_id=post.id,
            )
            for post in posts
        ]
