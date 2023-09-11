import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pytz

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleRedditConfig(BaseConnectorConfig):
    subreddit_name: str
    client_id: Optional[str]
    client_secret: Optional[str]
    user_agent: str
    search_query: Optional[str]
    num_posts: int

    def __post_init__(self):
        if self.num_posts <= 0:
            raise ValueError("The number of Reddit posts to fetch must be positive.")


@dataclass
class RedditFileMeta:
    date_created: str
    date_modified: str
    version: str


@dataclass
class RedditIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleRedditConfig = field(repr=False)
    post_id: str
    file_exists = None
    file_metadata: Optional[RedditFileMeta] = None
    registry_name: str = "reddit"

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @requires_dependencies(["praw"])
    def get_post(self):
        from praw import Reddit
        from praw.models import Submission

        try:
            reddit = Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                user_agent=self.config.user_agent,
            )
            post = Submission(reddit, self.post_id)
        except Exception as e:
            logger.error(f"Failed to retrieve post with id {self.post_id}")
            self.file_exists = False
            raise

        self.file_exists = (self.post.author != "[deleted]" or self.post.auth is not None) and (
            self.post.selftext != "[deleted]" or self.post.selftext != "[removed]"
        )
        return post

    def get_file_metadata(self):
        post = self.get_post()
        self.file_metadata = RedditFileMeta(
            datetime.fromtimestamp(self.post.created_utc, pytz.utc).isoformat(),
            None,
            post.permalink,
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        # Write the title plus the body, if any
        post = self.get_post()
        text_to_write = f"# {post.title}\n{post.selftext}"
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(text_to_write)

    @property
    def filename(self) -> Path:
        return (Path(self.standard_config.download_dir) / f"{self.post_id}.md").resolve()

    @property
    def _output_filename(self):
        return Path(self.standard_config.output_dir) / f"{self.post_id}.json"

    @property
    def date_created(self) -> Optional[str]:
        if not self.file_metadata:
            self.get_file_metadata()
        return self.file_metadata.date_created

    @property
    def exists(self) -> Optional[bool]:
        if self.file_exists is None:
            self.get_file_metadata()
        return self.file_exists

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:
        return {"id": self.post.id}

    @property
    def version(self) -> Optional[str]:
        if not self.file_metadata:
            self.get_file_metadata()
        return self.file_metadata.version


@requires_dependencies(["praw"], extras="reddit")
class RedditConnector(ConnectorCleanupMixin, BaseConnector):
    config: SimpleRedditConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleRedditConfig):
        from praw import Reddit

        super().__init__(standard_config, config)
        self.reddit = Reddit(
            client_id=config.client_id,
            client_secret=config.client_secret,
            user_agent=config.user_agent,
        )

    def initialize(self):
        pass

    def get_ingest_docs(self):
        subreddit = self.reddit.subreddit(self.config.subreddit_name)
        if self.config.search_query:
            posts = subreddit.search(self.config.search_query, limit=self.config.num_posts)
        else:
            posts = subreddit.hot(limit=self.config.num_posts)
        return [RedditIngestDoc(self.standard_config, self.config, post.id) for post in posts]
