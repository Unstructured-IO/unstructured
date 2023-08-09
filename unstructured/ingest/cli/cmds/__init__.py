from .azure import get_cmd as azure
from .biomed import get_cmd as biomed
from .box import get_cmd as box
from .confluence import get_cmd as confluence
from .discord import get_cmd as discord
from .dropbox import get_cmd as dropbox
from .elasticsearch import get_cmd as elasticsearch
from .fsspec import get_cmd as fsspec
from .gcs import get_cmd as gcs
from .github import get_cmd as github
from .gitlab import get_cmd as gitlab
from .google_drive import get_cmd as gdrive
from .local import get_cmd as local
from .notion import get_cmd as notion
from .onedrive import get_cmd as onedrive
from .outlook import get_cmd as outlook
from .reddit import get_cmd as reddit
from .s3 import get_cmd as s3
from .sharepoint import get_cmd as sharepoint
from .slack import get_cmd as slack
from .wikipedia import get_cmd as wikipedia

__all__ = [
    "azure",
    "biomed",
    "box",
    "confluence",
    "discord",
    "dropbox",
    "elasticsearch",
    "fsspec",
    "gcs",
    "gdrive",
    "github",
    "gitlab",
    "local",
    "notion",
    "onedrive",
    "outlook",
    "reddit",
    "s3",
    "sharepoint",
    "slack",
    "wikipedia",
]
