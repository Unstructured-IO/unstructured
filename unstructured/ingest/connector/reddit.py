import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
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
    client_id: str
    client_secret: str
    user_agent: str
    search_query: str
    num_posts: int

    def __post_init__(self):
        if self.num_posts <= 0:
            raise ValueError("The number of Reddit posts to fetch must be positive.")


@dataclass
class RedditIngestDoc(BaseIngestDoc, IngestDocCleanupMixin):
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
class RedditConnector(BaseConnector):
    config: SimpleRedditConfig

    def __init__(self, standard_config: StandardConnectorConfig, config: SimpleRedditConfig):
        from praw import Reddit

        super().__init__(standard_config, config)
        self.reddit = Reddit(
            client_id=config.client_id,
            client_secret=config.client_secret,
            user_agent=config.user_agent,
        )
        self.cleanup_files = (
            not standard_config.preserve_downloads and not standard_config.download_only
        )

    def cleanup(self, cur_dir=None):
        if not self.cleanup_files:
            return

        if cur_dir is None:
            cur_dir = self.standard_config.download_dir
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
        pass

    def get_ingest_docs(self):
        subreddit = self.reddit.subreddit(self.config.subreddit_name)
        if self.config.search_query:
            posts = subreddit.search(self.config.search_query, limit=self.config.num_posts)
        else:
            posts = subreddit.hot(limit=self.config.num_posts)
        return [RedditIngestDoc(self.standard_config, self.config, post) for post in posts]
