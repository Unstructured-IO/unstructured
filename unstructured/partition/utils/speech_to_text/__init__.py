"""Speech-to-text agents for transcribing audio in the multimodal partition pipeline."""

from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
    SpeechToTextAgent,
    TranscriptionSegment,
)

__all__ = ["SpeechToTextAgent", "TranscriptionSegment"]
