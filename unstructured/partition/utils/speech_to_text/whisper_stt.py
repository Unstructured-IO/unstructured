"""Whisper-based speech-to-text agent for the audio partitioner."""

from __future__ import annotations

from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
    SpeechToTextAgent,
)


class SpeechToTextAgentWhisper(SpeechToTextAgent):
    """Speech-to-text implementation using OpenAI Whisper."""

    def __init__(self, model_size: str = "base") -> None:
        """Initialize the Whisper model.

        Parameters
        ----------
        model_size
            Whisper model size: "tiny", "base", "small", "medium", "large", or "large-v3".
            Larger models are more accurate but slower and use more memory.
        """
        import whisper

        self._model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str, *, language: str | None = None) -> str:
        """Transcribe audio file to text using Whisper."""
        options: dict = {}
        if language is not None:
            options["language"] = language
        result = self._model.transcribe(audio_path, **options)
        return result.get("text", "").strip()
