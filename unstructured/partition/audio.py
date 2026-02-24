"""Partition audio files into elements using speech-to-text transcription."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import IO, Any

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, NarrativeText
from unstructured.file_utils.model import FileType
from unstructured.partition.common.common import exactly_one
from unstructured.partition.common.metadata import apply_metadata, get_last_modified_date
from unstructured.partition.utils.config import env_config
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

    Transcribes the audio and returns a single NarrativeText element containing
    the full transcript. Requires the optional `audio` extra with Whisper:
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
        if file is None:
            raise ValueError("Either filename or file must be provided.")
        file.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(file.read())
            audio_path = tmp.name

    try:
        agent_module = stt_agent or env_config.STT_AGENT
        agent = SpeechToTextAgent.get_instance(agent_module)
        text = agent.transcribe(audio_path, language=language)
    finally:
        if filename is None and audio_path.startswith(tempfile.gettempdir()):
            Path(audio_path).unlink(missing_ok=True)

    if not text.strip():
        return []

    metadata_kwargs: dict[str, Any] = {}
    if metadata_filename:
        metadata_kwargs["filename"] = metadata_filename
    elif filename:
        metadata_kwargs["filename"] = filename
    if metadata_last_modified:
        metadata_kwargs["last_modified"] = metadata_last_modified
    elif filename:
        last_modified = get_last_modified_date(filename)
        if last_modified:
            metadata_kwargs["last_modified"] = last_modified

    element = NarrativeText(text=text)
    element.metadata.detection_origin = "speech_to_text"
    element.metadata.update(element.metadata.__class__(**metadata_kwargs))

    return [element]
