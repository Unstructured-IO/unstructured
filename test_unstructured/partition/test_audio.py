# pyright: reportPrivateUsage=false

"""Tests for partition_audio (speech-to-text in multimodal pipeline)."""

from __future__ import annotations

import tempfile
from pathlib import Path
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
    mock_agent.transcribe.return_value = "Hello, this is a test transcript."

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
    mock_agent.transcribe.assert_called_once_with(path, language=None)


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_instance",
)
def test_partition_audio_from_file_uses_temp_path_and_cleans_up(mock_get_instance):
    mock_agent = mock_get_instance.return_value
    mock_agent.transcribe.return_value = "From file object."

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
    mock_agent.transcribe.return_value = "   "

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)
        tmp.flush()

    try:
        elements = partition_audio(filename=path)
    finally:
        Path(path).unlink(missing_ok=True)

    assert elements == []


def test_wav_file_type_is_partitionable():
    assert FileType.WAV.is_partitionable
    assert FileType.WAV.partitioner_shortname == "audio"
    assert FileType.WAV.partitioner_function_name == "partition_audio"
