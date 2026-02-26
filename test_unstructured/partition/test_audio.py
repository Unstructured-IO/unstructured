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
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
    try:
        with pytest.raises(ValueError, match="Exactly one of .* must be specified"):
            with open(path, "rb") as f:
                partition_audio(filename=path, file=f)
    finally:
        Path(path).unlink(missing_ok=True)


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_agent",
)
def test_partition_audio_from_filename_returns_transcript_elements(mock_get_agent):
    mock_agent = mock_get_agent.return_value
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
    mock_get_agent.assert_called_once_with(None)
    mock_agent.transcribe_segments.assert_called_once_with(path, language=None)


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_agent",
)
def test_partition_audio_from_file_uses_temp_path_and_cleans_up(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "From file object.", "start": 0.0, "end": 1.0},
    ]

    captured_temp_path: list[str] = []
    real_named_temp = tempfile.NamedTemporaryFile

    def spy_named_temp(*args, **kwargs):
        ctx = real_named_temp(*args, **kwargs)
        captured_temp_path.append(ctx.name)
        return ctx

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"\x00" * 44)
        tmp.flush()
        tmp.seek(0)
        with patch("unstructured.partition.audio.tempfile.NamedTemporaryFile", spy_named_temp):
            elements = partition_audio(file=tmp, metadata_filename="recording.wav")

    assert len(elements) == 1
    assert elements[0].text == "From file object."
    assert elements[0].metadata.filename == "recording.wav"
    assert len(captured_temp_path) == 1, "expected exactly one temp file to be created"
    assert not Path(captured_temp_path[0]).exists(), "temp file was not deleted after partitioning"


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_agent",
)
def test_partition_audio_cleans_up_temp_file_when_transcription_raises(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.side_effect = RuntimeError("transcription failed")

    captured_temp_path: list[str] = []
    real_named_temp = tempfile.NamedTemporaryFile

    def spy_named_temp(*args, **kwargs):
        ctx = real_named_temp(*args, **kwargs)
        captured_temp_path.append(ctx.name)
        return ctx

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"\x00" * 44)
        tmp.flush()
        tmp.seek(0)
        with patch("unstructured.partition.audio.tempfile.NamedTemporaryFile", spy_named_temp):
            with pytest.raises(RuntimeError, match="transcription failed"):
                partition_audio(file=tmp)

    assert len(captured_temp_path) == 1, "expected exactly one temp file to be created"
    assert not Path(captured_temp_path[0]).exists(), "temp file was not deleted after exception"


@patch(
    "unstructured.partition.audio.SpeechToTextAgent.get_agent",
)
def test_partition_audio_empty_transcript_returns_empty_list(mock_get_agent):
    mock_agent = mock_get_agent.return_value
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
    "unstructured.partition.audio.SpeechToTextAgent.get_agent",
)
def test_partition_audio_returns_one_element_per_segment(mock_get_agent):
    mock_agent = mock_get_agent.return_value
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


# ================================================================================================
# partition_audio parameter forwarding
# ================================================================================================


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
def test_partition_audio_forwards_custom_stt_agent_to_get_agent(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "Custom agent output.", "start": 0.0, "end": 1.0},
    ]
    custom_module = (
        "unstructured.partition.utils.speech_to_text.whisper_stt.SpeechToTextAgentWhisper"
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)
        tmp.flush()

    try:
        partition_audio(filename=path, stt_agent=custom_module)
    finally:
        Path(path).unlink(missing_ok=True)

    mock_get_agent.assert_called_once_with(custom_module)


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
def test_partition_audio_forwards_language_to_transcribe_segments(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "Hola mundo.", "start": 0.0, "end": 1.5},
    ]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)
        tmp.flush()

    try:
        elements = partition_audio(filename=path, language="es")
    finally:
        Path(path).unlink(missing_ok=True)

    mock_agent.transcribe_segments.assert_called_once_with(path, language="es")
    assert elements[0].text == "Hola mundo."


# ================================================================================================
# Whitespace-only segment filtering
# ================================================================================================


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
def test_partition_audio_filters_whitespace_only_segments(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "  ", "start": 0.0, "end": 0.5},
        {"text": "Real content.", "start": 0.5, "end": 2.0},
        {"text": "\t\n", "start": 2.0, "end": 2.5},
    ]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
        tmp.write(b"\x00" * 44)
        tmp.flush()

    try:
        elements = partition_audio(filename=path)
    finally:
        Path(path).unlink(missing_ok=True)

    assert len(elements) == 1
    assert elements[0].text == "Real content."


# ================================================================================================
# SpeechToTextAgent unit tests
# ================================================================================================


class TestSpeechToTextAgentInterface:
    """Unit tests for the SpeechToTextAgent base class."""

    def test_get_agent_uses_env_config_when_no_module_given(self):
        from unittest.mock import patch as _patch

        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        with _patch.object(SpeechToTextAgent, "get_instance") as mock_get_instance:
            SpeechToTextAgent.get_agent(None)
            called_with = mock_get_instance.call_args[0][0]
            assert "SpeechToTextAgent" in called_with or "Whisper" in called_with

    def test_get_agent_passes_explicit_module_to_get_instance(self):
        from unittest.mock import patch as _patch

        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        custom = "unstructured.partition.utils.speech_to_text.whisper_stt.SpeechToTextAgentWhisper"
        with _patch.object(SpeechToTextAgent, "get_instance") as mock_get_instance:
            SpeechToTextAgent.get_agent(custom)
            mock_get_instance.assert_called_once_with(custom)

    def test_get_instance_rejects_non_whitelisted_module(self):
        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        with pytest.raises(ValueError, match="must be in the whitelist"):
            SpeechToTextAgent.get_instance("evil.module.EvilAgent")

    def test_transcribe_segments_default_delegates_to_transcribe(self):
        """Base transcribe_segments() wraps transcribe() in a single segment."""

        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        # Create a minimal concrete subclass
        class _StubAgent(SpeechToTextAgent):
            def transcribe(self, audio_path: str, *, language=None) -> str:
                return "stub text"

        agent = _StubAgent()
        segments = agent.transcribe_segments("fake.wav")
        assert len(segments) == 1
        assert segments[0]["text"] == "stub text"
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 0.0

    def test_transcribe_segments_default_returns_empty_for_blank_text(self):
        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        class _BlankAgent(SpeechToTextAgent):
            def transcribe(self, audio_path: str, *, language=None) -> str:
                return "   "

        agent = _BlankAgent()
        assert agent.transcribe_segments("fake.wav") == []
