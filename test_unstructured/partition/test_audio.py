# pyright: reportPrivateUsage=false

"""Tests for partition_audio (speech-to-text in multimodal pipeline)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import IO
from unittest.mock import patch

import pytest

from unstructured.documents.elements import NarrativeText
from unstructured.file_utils.model import FileType
from unstructured.partition.audio import partition_audio


def test_partition_audio_raises_with_neither_filename_nor_file():
    with pytest.raises(ValueError, match="Exactly one of .* must be specified"):
        partition_audio()


def test_partition_audio_raises_with_both_filename_and_file():
    with pytest.raises(ValueError, match="Exactly one of .* must be specified"):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            partition_audio(filename=tmp.name, file=tmp)


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_instance",
)
def test_partition_audio_from_filename_returns_transcript_elements(mock_get_instance):
    mock_agent = mock_get_instance.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "Hello, this is a test transcript.", "start": 0.0, "end": 2.5},
    ]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)  # minimal WAV-like header
        tmp.flush()

    try:
        elements = partition_audio(filename=path)
    finally:
        Path(path).unlink(missing_ok=True)

    assert len(elements) == 1
    assert isinstance(elements[0], NarrativeText)
    assert elements[0].text == "Hello, this is a test transcript."
    assert elements[0].metadata.detection_origin == "speech_to_text"
    assert elements[0].metadata.segment_start_seconds == 0.0
    assert elements[0].metadata.segment_end_seconds == 2.5
    mock_agent.transcribe_segments.assert_called_once_with(path, language=None)


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_instance",
)
def test_partition_audio_from_file_uses_temp_path_and_cleans_up(mock_get_instance):
    mock_agent = mock_get_instance.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "From file object.", "start": 0.0, "end": 1.0},
    ]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"\x00" * 44)
        tmp.flush()
        tmp.seek(0)
        elements = partition_audio(file=tmp, metadata_filename="recording.wav")

    assert len(elements) == 1
    assert elements[0].text == "From file object."
    assert elements[0].metadata.filename == "recording.wav"


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_instance",
)
def test_partition_audio_empty_transcript_returns_empty_list(mock_get_instance):
    mock_agent = mock_get_instance.return_value
    mock_agent.transcribe_segments.return_value = []

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)
        tmp.flush()

    try:
        elements = partition_audio(filename=path)
    finally:
        Path(path).unlink(missing_ok=True)

    assert elements == []


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_instance",
)
def test_partition_audio_returns_one_element_per_segment(mock_get_instance):
    mock_agent = mock_get_instance.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "First segment.", "start": 0.0, "end": 1.0},
        {"text": "Second segment.", "start": 1.0, "end": 2.5},
        {"text": "Third segment.", "start": 2.5, "end": 4.0},
    ]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)
        tmp.flush()

    try:
        elements = partition_audio(filename=path)
    finally:
        Path(path).unlink(missing_ok=True)

    assert len(elements) == 3
    assert elements[0].text == "First segment."
    assert elements[0].metadata.segment_start_seconds == 0.0
    assert elements[0].metadata.segment_end_seconds == 1.0
    assert elements[1].text == "Second segment."
    assert elements[1].metadata.segment_start_seconds == 1.0
    assert elements[1].metadata.segment_end_seconds == 2.5
    assert elements[2].text == "Third segment."
    assert elements[2].metadata.segment_start_seconds == 2.5
    assert elements[2].metadata.segment_end_seconds == 4.0


@pytest.mark.parametrize(
    ("metadata_filename", "file_name", "expected"),
    [
        ("recording.mp3", None, ".mp3"),
        ("recording.mp3", "other.wav", ".mp3"),  # metadata_filename wins
        (None, "audio.flac", ".flac"),
        (None, None, ".wav"),  # fallback
        ("noext", None, ".wav"),  # no extension → fallback
    ],
)
def test_audio_suffix(metadata_filename, file_name, expected):
    from io import BytesIO

    from unstructured.partition.audio import _audio_suffix

    f: IO[bytes] = BytesIO(b"")
    if file_name is not None:
        f.name = file_name  # type: ignore[attr-defined]
    assert _audio_suffix(f, metadata_filename) == expected


def test_wav_file_type_is_partitionable():
    assert FileType.WAV.is_partitionable
    assert FileType.WAV.partitioner_shortname == "audio"
    assert FileType.WAV.partitioner_function_name == "partition_audio"
