"""Abstract interface for speech-to-text (STT) agents used by the audio partitioner."""

from __future__ import annotations

import functools
import importlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from unstructured.logger import logger
from unstructured.partition.utils.constants import STT_AGENT_MODULES_WHITELIST

if TYPE_CHECKING:
    pass


class SpeechToTextAgent(ABC):
    """Defines the interface for a speech-to-text transcription service."""

    @staticmethod
    @functools.lru_cache(maxsize=1)
    def get_instance(agent_module: str) -> "SpeechToTextAgent":
        """Load and return the configured SpeechToTextAgent implementation.

        The implementation is determined by the `STT_AGENT` environment variable
        or the passed `agent_module` (e.g. whisper implementation).
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
