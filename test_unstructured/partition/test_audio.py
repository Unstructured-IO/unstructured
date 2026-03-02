# pyright: reportPrivateUsage=false

"""Tests for partition_audio (speech-to-text in multimodal pipeline)."""

from __future__ import annotations

import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Generator
from unittest.mock import MagicMock, patch

import pytest

from unstructured.documents.elements import NarrativeText
from unstructured.file_utils.model import FileType
from unstructured.partition.audio import partition_audio

# ================================================================================================
# Shared fixtures
# ================================================================================================

_ONE_SEGMENT = [{"text": "Hello, world.", "start": 0.0, "end": 1.0}]


@contextmanager
def _tmp_audio(suffix: str = ".wav", content: bytes = b"\x00" * 44) -> Generator[str, None, None]:
    """Yield the path to a temporary audio file, deleting it on exit."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp.flush()
        path = tmp.name
    try:
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.fixture
def mock_stt_agent() -> Generator[MagicMock, None, None]:
    """Patch SpeechToTextAgent.get_agent and yield the mock agent instance.

    Tests that only need a working agent (and don't care about call details) can use
    this fixture directly. Tests that need to inspect mock calls should use
    ``@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")`` directly so
    the mock is visible in the function signature.
    """
    with patch("unstructured.partition.audio.SpeechToTextAgent.get_agent") as mock_get_agent:
        agent = mock_get_agent.return_value
        agent.transcribe_segments.return_value = _ONE_SEGMENT
        yield agent


# ================================================================================================
# Input validation
# ================================================================================================


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


# ================================================================================================
# Core element output
# ================================================================================================


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
def test_partition_audio_from_filename_returns_transcript_elements(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "Hello, this is a test transcript.", "start": 0.0, "end": 2.5},
    ]

    with _tmp_audio() as path:
        elements = partition_audio(filename=path)

    assert len(elements) == 1
    assert isinstance(elements[0], NarrativeText)
    assert elements[0].text == "Hello, this is a test transcript."
    assert elements[0].metadata.detection_origin == "speech_to_text"
    assert elements[0].metadata.segment_start_seconds == 0.0
    assert elements[0].metadata.segment_end_seconds == 2.5
    mock_get_agent.assert_called_once_with(None)
    mock_agent.transcribe_segments.assert_called_once_with(path, language=None)


def test_partition_audio_empty_transcript_returns_empty_list(mock_stt_agent):
    mock_stt_agent.transcribe_segments.return_value = []
    with _tmp_audio() as path:
        assert partition_audio(filename=path) == []


def test_partition_audio_returns_one_element_per_segment(mock_stt_agent):
    mock_stt_agent.transcribe_segments.return_value = [
        {"text": "First segment.", "start": 0.0, "end": 1.0},
        {"text": "Second segment.", "start": 1.0, "end": 2.5},
        {"text": "Third segment.", "start": 2.5, "end": 4.0},
    ]

    with _tmp_audio() as path:
        elements = partition_audio(filename=path)

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


def test_partition_audio_filters_whitespace_only_segments(mock_stt_agent):
    mock_stt_agent.transcribe_segments.return_value = [
        {"text": "  ", "start": 0.0, "end": 0.5},
        {"text": "Real content.", "start": 0.5, "end": 2.0},
        {"text": "\t\n", "start": 2.0, "end": 2.5},
    ]

    with _tmp_audio() as path:
        elements = partition_audio(filename=path)

    assert len(elements) == 1
    assert elements[0].text == "Real content."


# ================================================================================================
# Temp-file lifecycle (file-object input)
# ================================================================================================


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
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


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
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


# ================================================================================================
# MIME type / filetype metadata
# ================================================================================================


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
@patch("unstructured.partition.audio.detect_filetype")
def test_partition_audio_stamps_correct_mime_type_for_detected_format(mock_detect, mock_get_agent):
    """metadata.filetype reflects the actual detected audio format, not a hardcoded WAV."""
    mock_detect.return_value = FileType.MP3
    mock_get_agent.return_value.transcribe_segments.return_value = [
        {"text": "MP3 content.", "start": 0.0, "end": 1.0},
    ]

    with _tmp_audio(suffix=".mp3", content=b"\xff\xfb" + b"\x00" * 42) as path:
        elements = partition_audio(filename=path)

    assert len(elements) == 1
    assert elements[0].metadata.filetype == FileType.MP3.mime_type  # "audio/mpeg"


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
@patch("unstructured.partition.audio.detect_filetype")
def test_partition_audio_falls_back_to_wav_mime_type_when_format_undetectable(
    mock_detect, mock_get_agent
):
    """When filetype detection returns UNK, metadata.filetype falls back to audio/wav."""
    mock_detect.return_value = FileType.UNK
    mock_get_agent.return_value.transcribe_segments.return_value = [
        {"text": "Unknown format.", "start": 0.0, "end": 1.0},
    ]

    with _tmp_audio() as path:
        elements = partition_audio(filename=path)

    assert len(elements) == 1
    assert elements[0].metadata.filetype == FileType.WAV.mime_type  # "audio/wav"


# ================================================================================================
# FileType model
# ================================================================================================


@pytest.mark.parametrize(
    "file_type",
    [
        FileType.FLAC,
        FileType.M4A,
        FileType.MP3,
        FileType.OGG,
        FileType.OPUS,
        FileType.WAV,
        FileType.WEBM,
    ],
)
def test_audio_file_types_are_partitionable(file_type: FileType):
    assert file_type.is_partitionable
    assert file_type.partitioner_shortname == "audio"
    assert file_type.partitioner_function_name == "partition_audio"
    assert file_type.extra_name == "audio"
    assert file_type.importable_package_dependencies == ("whisper",)


# ================================================================================================
# _audio_suffix helper
# ================================================================================================


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


# ================================================================================================
# partition_audio parameter forwarding
# ================================================================================================


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
def test_partition_audio_forwards_custom_stt_agent_to_get_agent(mock_get_agent):
    mock_get_agent.return_value.transcribe_segments.return_value = _ONE_SEGMENT
    custom_module = (
        "unstructured.partition.utils.speech_to_text.whisper_stt.SpeechToTextAgentWhisper"
    )

    with _tmp_audio() as path:
        partition_audio(filename=path, stt_agent=custom_module)

    mock_get_agent.assert_called_once_with(custom_module)


@patch("unstructured.partition.audio.SpeechToTextAgent.get_agent")
def test_partition_audio_forwards_language_to_transcribe_segments(mock_get_agent):
    mock_agent = mock_get_agent.return_value
    mock_agent.transcribe_segments.return_value = [
        {"text": "Hola mundo.", "start": 0.0, "end": 1.5},
    ]

    with _tmp_audio() as path:
        elements = partition_audio(filename=path, language="es")

    mock_agent.transcribe_segments.assert_called_once_with(path, language="es")
    assert elements[0].text == "Hola mundo."


# ================================================================================================
# SpeechToTextAgent unit tests
# ================================================================================================


class TestSpeechToTextAgentInterface:
    """Unit tests for the SpeechToTextAgent base class."""

    def test_get_agent_uses_env_config_when_no_module_given(self):
        import os
        from unittest.mock import patch as _patch

        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        sentinel = "unstructured.partition.utils.speech_to_text.whisper_stt.SentinelAgent"
        with (
            _patch.dict(os.environ, {"STT_AGENT": sentinel}),
            _patch.object(SpeechToTextAgent, "get_instance") as mock_get_instance,
        ):
            SpeechToTextAgent.get_agent(None)
            mock_get_instance.assert_called_once_with(sentinel)

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

    def test_transcribe_default_joins_segments(self):
        """Base transcribe() joins segment texts from transcribe_segments()."""
        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
            TranscriptionSegment,
        )

        class _StubAgent(SpeechToTextAgent):
            def transcribe_segments(self, audio_path: str, *, language=None):
                return [
                    TranscriptionSegment(text="Hello", start=0.0, end=1.0),
                    TranscriptionSegment(text="world.", start=1.0, end=2.0),
                ]

        agent = _StubAgent()
        assert agent.transcribe("fake.wav") == "Hello world."

    def test_transcribe_default_returns_empty_string_for_no_segments(self):
        """Base transcribe() returns empty string when transcribe_segments() returns []."""
        from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
            SpeechToTextAgent,
        )

        class _SilentAgent(SpeechToTextAgent):
            def transcribe_segments(self, audio_path: str, *, language=None):
                return []

        agent = _SilentAgent()
        assert agent.transcribe("fake.wav") == ""
