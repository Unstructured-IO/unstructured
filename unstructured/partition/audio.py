"""Partitioner for Excel 2007+ (XLSX) spreadsheets."""

from __future__ import annotations

import io
from tempfile import SpooledTemporaryFile
from typing import IO, Any, Iterator, Optional

import networkx as nx
import numpy as np
import pandas as pd
from typing_extensions import Self, TypeAlias

from unstructured.chunking import add_chunking_strategy
from unstructured.cleaners.core import clean_bullets
from unstructured.common.html_table import HtmlTable
from unstructured.documents.elements import (
    Element,
    TranscriptFragment,
    ElementMetadata
)
from unstructured.file_utils.model import FileType
from unstructured.partition.common.metadata import apply_metadata
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
import os


@apply_metadata(FileType.MP3)
@add_chunking_strategy
def partition_audio(
    filename: Optional[str] = None,
    *,
    file: Optional[IO[bytes]] = None,
    **kwargs: Any
) -> list[Element]:

    deepgram_key = os.getenv("DEEPGRAM_API_KEY")

    if deepgram_key is not None:
        deepgram = DeepgramClient(deepgram_key)

        if filename is not None:
            with open(filename, "rb") as file:
                audio_data = file.read()
        elif file is not None:
            audio_data = file.read()
        else:
            raise ValueError("No audio file provided.")

        payload: FileSource = {
            "buffer": audio_data
        }

        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True
        )

        response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)

        elements = []
        for channel in response.results.channels:
            for alt in channel.alternatives:
                langs = alt.languages
                for paragraph in alt.paragraphs.paragraphs:
                    elements.append(TranscriptFragment(
                        text=' '.join([sentance.text for sentance in paragraph.sentences]),
                        metadata=ElementMetadata(
                            languages=langs or [],
                            start_time=paragraph.start,
                            end_time=paragraph.end
                        )
                    ))
        return elements

    else:
        # implement whisper version?
        raise ValueError("Deepgram API key not found. No other audio partitioning methods are available.")