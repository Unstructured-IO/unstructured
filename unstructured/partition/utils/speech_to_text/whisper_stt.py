"""Whisper-based speech-to-text agent for the audio partitioner."""

from __future__ import annotations

import threading

from unstructured.partition.utils.config import env_config
from unstructured.partition.utils.speech_to_text.speech_to_text_interface import (
    SpeechToTextAgent,
    TranscriptionSegment,
)


class SpeechToTextAgentWhisper(SpeechToTextAgent):
    """Speech-to-text implementation using OpenAI Whisper.

    **Concurrency model** — a single instance is shared across all callers via the
    ``lru_cache`` in :meth:`~SpeechToTextAgent.get_instance`. Because
    ``whisper.model.transcribe()`` is not documented as thread-safe, a per-instance
    ``threading.Lock`` serializes all transcription calls. This prevents data races but
    means the process can only run one transcription at a time for the default agent —
    a hidden throughput ceiling under concurrent workloads. For true parallelism, use
    process-based concurrency (e.g. ``multiprocessing`` or separate worker processes)
    rather than threads.

    **Configuration snapshot** — model size, device, and FP16 flag are read from
    environment variables (``WHISPER_MODEL_SIZE``, ``WHISPER_DEVICE``, ``WHISPER_FP16``)
    at construction time and frozen for the lifetime of the cached instance. Changing
    those variables after the first call has no effect without a process restart.
    """

    def __init__(self, model_size: str | None = None) -> None:
        """Initialize the Whisper model.

        Parameters
        ----------
        model_size
            Whisper model size: "tiny", "base", "small", "medium", "large", or "large-v3".
            Larger models are more accurate but slower and use more memory.
            When None, uses the WHISPER_MODEL_SIZE environment variable (default \"base\").
        """
        import whisper

        size = model_size if model_size is not None else env_config.WHISPER_MODEL_SIZE
        device = env_config.WHISPER_DEVICE.strip() or None  # empty -> auto
        try:
            self._model = whisper.load_model(size, device=device)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load Whisper model '{size}' on device {device!r}. "
                "Possible causes: invalid model name, network error during model download, "
                "or insufficient GPU memory (CUDA OOM). "
                f"Valid model sizes: tiny, base, small, medium, large, large-v3. "
                f"Original error: {exc}"
            ) from exc
        self._fp16 = env_config.WHISPER_FP16
        self._lock = threading.Lock()

    def transcribe_segments(
        self, audio_path: str, *, language: str | None = None
    ) -> list[TranscriptionSegment]:
        """Transcribe audio and return one segment per Whisper segment with timestamps."""
        options: dict = {"fp16": self._fp16}
        if language is not None:
            options["language"] = language
        with self._lock:
            result = self._model.transcribe(audio_path, **options)
        segments: list[TranscriptionSegment] = []
        for seg in result.get("segments", []):
            segments.append(
                TranscriptionSegment(
                    text=(seg.get("text") or ""),
                    start=float(seg.get("start", 0)),
                    end=float(seg.get("end", 0)),
                )
            )
        if not segments and result.get("text", "").strip():
            segments = [
                TranscriptionSegment(
                    text=result.get("text", "").strip(),
                    start=0.0,
                    end=0.0,
                )
            ]
        return segments
