"""Abstract interface for speech-to-text (STT) agents used by the audio partitioner."""

from __future__ import annotations

import functools
import importlib
from abc import ABC, abstractmethod
from typing import TypedDict

from unstructured.logger import logger
from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.constants import STT_AGENT_MODULES_WHITELIST


class TranscriptionSegment(TypedDict):
    """A single segment of a transcription with text and timestamps in seconds."""

    text: str
    start: float
    end: float


class SpeechToTextAgent(ABC):
    """Defines the interface for a speech-to-text transcription service."""

    @classmethod
    def get_agent(cls, agent_module: str | None = None) -> "SpeechToTextAgent":
        """Return the configured SpeechToTextAgent instance.

        The agent module is resolved from `agent_module` when provided, otherwise from
        the `STT_AGENT` environment variable (default: Whisper).
        """
        return cls.get_instance(agent_module or env_config.STT_AGENT)

    @staticmethod
    @functools.lru_cache(maxsize=env_config.STT_AGENT_CACHE_SIZE)
    def get_instance(agent_module: str) -> "SpeechToTextAgent":
        """Load and return a SpeechToTextAgent for the given fully-qualified class name.

        Results are cached up to STT_AGENT_CACHE_SIZE entries.
        """
        module_name, class_name = agent_module.rsplit(".", 1)
        if module_name not in STT_AGENT_MODULES_WHITELIST:
            raise ValueError(
                f"Speech-to-text agent module {module_name} must be in the whitelist: "
                f"{STT_AGENT_MODULES_WHITELIST}."
            )
        try:
            mod = importlib.import_module(module_name)
            cls = getattr(mod, class_name)
            return cls()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to get SpeechToTextAgent instance: {e}")
            raise RuntimeError(
                "Could not load the SpeechToText agent. Install the audio extra: "
                'pip install "unstructured[audio]"'
            ) from e

    @abstractmethod
    def transcribe(self, audio_path: str, *, language: str | None = None) -> str:
        """Transcribe audio from a file path to text.

        Parameters
        ----------
        audio_path
            Path to an audio file (e.g. WAV, MP3).
        language
            Optional ISO 639-1 language code for the spoken language (e.g. "en").
            When None, the agent may auto-detect.

        Returns
        -------
        Transcribed text.
        """
        pass

    def transcribe_segments(
        self, audio_path: str, *, language: str | None = None
    ) -> list[TranscriptionSegment]:
        """Transcribe audio and return segment-level results with timestamps.

        Default implementation returns a single segment from transcribe() with start=0, end=0.
        Override in agents that support segment-level output (e.g. Whisper).

        Parameters
        ----------
        audio_path
            Path to an audio file (e.g. WAV, MP3).
        language
            Optional ISO 639-1 language code for the spoken language (e.g. "en").

        Returns
        -------
        List of segments, each with "text" and optionally "start" and "end" (seconds).
        """
        text = self.transcribe(audio_path, language=language)
        if not text.strip():
            return []
        return [TranscriptionSegment(text=text.strip(), start=0.0, end=0.0)]
