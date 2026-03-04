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
    """A single segment of a transcription with text and timestamps in seconds.

    The audio partitioner (caller of :meth:`SpeechToTextAgent.transcribe_segments`) treats
    empty or whitespace-only ``text`` as absent: it strips each segment's text and skips
    segments that are empty after stripping. Agents may therefore return such segments
    without filtering; the partitioner is the single place that drops them.
    """

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

        Results are cached (keyed on ``agent_module``) up to ``STT_AGENT_CACHE_SIZE``
        entries. Because the cache key is the class name only, model-configuration
        environment variables (``WHISPER_MODEL_SIZE``, ``WHISPER_DEVICE``,
        ``WHISPER_FP16``) are read once at first instantiation and ignored on subsequent
        calls. A process restart is required to pick up configuration changes.
        """
        module_name, class_name = agent_module.rsplit(".", 1)
        if module_name not in STT_AGENT_MODULES_WHITELIST:
            raise ValueError(
                f"Speech-to-text agent module {module_name} must be in the whitelist: "
                f"{STT_AGENT_MODULES_WHITELIST}."
            )
        try:
            mod = importlib.import_module(module_name)
            loaded_class = getattr(mod, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load SpeechToTextAgent class '{agent_module}': {e}")
            raise RuntimeError(
                f"Could not load the SpeechToText agent class '{agent_module}'. "
                "Install the audio extra: "
                'pip install "unstructured[audio]"'
            ) from e

        if not isinstance(loaded_class, type):
            raise TypeError(
                f"'{agent_module}' does not refer to a class "
                f"(got {type(loaded_class).__name__}). "
                "Speech-to-text agent must be a subclass of SpeechToTextAgent."
            )
        if not issubclass(loaded_class, SpeechToTextAgent):
            raise TypeError(
                f"'{agent_module}' must be a subclass of SpeechToTextAgent, "
                f"got {loaded_class.__qualname__}."
            )
        try:
            return loaded_class()
        except Exception as e:
            logger.error(f"SpeechToTextAgent '{class_name}' loaded but failed to initialize: {e}")
            raise RuntimeError(
                f"SpeechToText agent '{class_name}' was imported successfully but its "
                f"constructor raised an error. "
                f"Original error: {e}"
            ) from e

    @abstractmethod
    def transcribe_segments(
        self, audio_path: str, *, language: str | None = None
    ) -> list[TranscriptionSegment]:
        """Transcribe audio and return segment-level results with timestamps.

        This is the **primary method** to implement. All partitioning calls go through
        here. Subclasses that support segment-level output (e.g. Whisper) should return
        one entry per segment; subclasses without native segment support should return a
        single segment with ``start=0.0`` and ``end=0.0``.

        Parameters
        ----------
        audio_path
            Path to an audio file (e.g. WAV, MP3).
        language
            Optional ISO 639-1 language code for the spoken language (e.g. ``"en"``).
            When ``None``, the agent may auto-detect.

        Returns
        -------
        List of :class:`TranscriptionSegment` dicts, each with ``"text"``, ``"start"``,
        and ``"end"`` keys. Return an empty list when the audio contains no speech.
        Segments with empty or whitespace-only ``text`` may be included; the partitioner
        will strip and drop them.
        """
