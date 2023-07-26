from .azure import azure
from .dropbox import dropbox
from .fsspec import fsspec
from .gcs import gcs
from .github import github
from .gitlab import gitlab
from .reddit import reddit
from .s3 import s3
from .slack import slack

__all__ = ["gcs", "s3", "dropbox", "azure", "fsspec", "github", "gitlab", "reddit", "slack"]
