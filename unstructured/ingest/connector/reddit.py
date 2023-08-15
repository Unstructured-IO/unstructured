import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

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

if TYPE_CHECKING:
    from praw.models import Submission


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
class RedditIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    config: SimpleRedditConfig = field(repr=False)
    post: "Submission"

    @property
    def filename(self) -> Path:
        return (Path(self.standard_config.download_dir) / f"{self.post.id}.md").resolve()

    @property
    def _output_filename(self):
        return Path(self.standard_config.output_dir) / f"{self.post.id}.json"

    def _create_full_tmp_dir_path(self):
        self.filename.parent.mkdir(parents=True, exist_ok=True)

    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        """Fetches the "remote" doc and stores it locally on the filesystem."""
        self._create_full_tmp_dir_path()
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")
        # Write the title plus the body, if any
        text_to_write = f"# {self.post.title}\n{self.post.selftext}"
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(text_to_write)


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
        return [RedditIngestDoc(self.standard_config, self.config, post) for post in posts]
