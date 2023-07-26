from .azure import azure
from .dropbox import dropbox
from .fsspec import fsspec
from .gcs import gcs
from .github import github
from .gitlab import gitlab
from .s3 import s3

__all__ = ["gcs", "s3", "dropbox", "azure", "fsspec", "github", "gitlab"]
