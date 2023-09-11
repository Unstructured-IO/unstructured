import os
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
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
    date_created: Optional[str] = None
    date_modified: Optional[str] = None
    source_url: Optional[str] = None
    exists: Optional[bool] = None


@dataclass
class RedditIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleRedditConfig = field(repr=False)
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
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                user_agent=self.config.user_agent,
            )
            post = Submission(reddit, self.post_id)
        except Exception:
            logger.error(f"Failed to retrieve post with id {self.post_id}")
            return None
        return post

    @cached_property
    def file_metadata(self) -> RedditFileMeta:
        post = self.get_post()
        if post is None:
            return RedditFileMeta(
                exists=False,
            )

        file_exists = (post.author != "[deleted]" or post.auth is not None) and (
            post.selftext != "[deleted]" or post.selftext != "[removed]"
        )

        return RedditFileMeta(
            datetime.fromtimestamp(post.created_utc, pytz.utc).isoformat(),
            None,
            post.permalink,
            file_exists,
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        # Write the title plus the body, if any
        post = self.get_post()
        if post is None:
            raise ValueError(
                f"Failed to retrieve post {self.post_id}",
            )

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
        return self.file_metadata.date_created

    @property
    def exists(self) -> Optional[bool]:
        return self.file_metadata.exists

    @property
    def record_locator(self) -> Optional[Dict[str, Any]]:
        return {
            "subreddit_name": self.config.subreddit_name,
            "id": self.post_id,
        }

    @property
    def source_url(self) -> Optional[str]:
        return self.file_metadata.source_url


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
