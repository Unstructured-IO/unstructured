from google_drive import gdrive

from .azure import azure
from .biomed import biomed
from .confluence import confluence
from .discord import discord
from .dropbox import dropbox
from .elasticsearch import elasticsearch
from .fsspec import fsspec
from .gcs import gcs
from .github import github
from .gitlab import gitlab
from .local import local
from .onedrive import onedrive
from .outlook import outlook
from .reddit import reddit
from .s3 import s3
from .slack import slack
from .wikipedia import wikipedia

__all__ = [
    "gcs",
    "s3",
    "dropbox",
    "azure",
    "fsspec",
    "github",
    "gitlab",
    "reddit",
    "slack",
    "discord",
    "wikipedia",
    "gdrive",
    "biomed",
    "onedrive",
    "outlook",
    "local",
    "elasticsearch",
    "confluence",
]
