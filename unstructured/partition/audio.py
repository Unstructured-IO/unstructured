"""Partition audio files into elements using speech-to-text transcription."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import IO, Any

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, ElementMetadata, NarrativeText
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
    SpeechToTextAgent,
)


@apply_metadata(FileType.WAV)
@add_chunking_strategy
def partition_audio(
    filename: str | None = None,
    *,
    file: IO[bytes] | None = None,
    language: str | None = None,
    stt_agent: str | None = None,
    metadata_filename: str | None = None,
    metadata_last_modified: str | None = None,
    **kwargs: Any,
) -> list[Element]:
    """Partition an audio file (e.g. WAV) into elements using speech-to-text.

    Transcribes the audio and returns one NarrativeText element per Whisper segment,
    preserving segment-level structure and timestamps in metadata (segment_start_seconds,
    segment_end_seconds). Requires the optional `audio` extra with Whisper:
    ``pip install "unstructured[audio]"``.

    Parameters
    ----------
    filename
        Path to the audio file.
    file
        File-like object opened in binary mode (e.g. ``open("audio.wav", "rb")``).
    language
        Optional ISO 639-1 language code for the spoken language (e.g. "en").
        When None, the speech-to-text agent may auto-detect.
    stt_agent
        Optional fully-qualified class name of the SpeechToTextAgent implementation.
        Defaults to the Whisper agent when the audio extra is installed.
    metadata_filename
        Filename to store in element metadata when partitioning from a file object.
    metadata_last_modified
        Last modified date to store in element metadata.
    """
    exactly_one(filename=filename, file=file)

    audio_path: str
    if filename is not None:
        audio_path = filename
    else:
        assert file is not None  # guaranteed by exactly_one()
        file.seek(0)
        suffix = _audio_suffix(file, metadata_filename)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(file, tmp)
            audio_path = tmp.name

    try:
        agent = SpeechToTextAgent.get_agent(stt_agent)
        segments = agent.transcribe_segments(audio_path, language=language)
    finally:
        if filename is None and audio_path.startswith(tempfile.gettempdir()):
            Path(audio_path).unlink(missing_ok=True)

    if not segments:
        return []

    base_metadata = ElementMetadata(
        last_modified=get_last_modified_date(filename) if filename else None,
    )
    base_metadata.detection_origin = "speech_to_text"

    elements: list[Element] = []
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        element = NarrativeText(text=text)
        element.metadata = ElementMetadata(
            last_modified=base_metadata.last_modified,
            segment_start_seconds=seg["start"],
            segment_end_seconds=seg["end"],
        )
        element.metadata.detection_origin = "speech_to_text"
        elements.append(element)

    return elements


def _audio_suffix(file: IO[bytes], metadata_filename: str | None) -> str:
    """Return the file-extension suffix for a temp file that wraps `file`.

    Preference order:
    1. Extension of `metadata_filename` when provided (e.g. ".mp3" from "recording.mp3").
    2. Extension of `file.name` when the file object exposes a name (e.g. a real opened file).
    3. ".wav" as a safe fallback recognised by all STT backends.
    """
    for name in (metadata_filename, getattr(file, "name", None)):
        if name:
            suffix = Path(name).suffix
            if suffix:
                return suffix
    return ".wav"
