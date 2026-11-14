import wave

import pytest

from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import ElementMetadata, Image, NarrativeText, Text
from unstructured.partition.audio import partition_audio


@pytest.mark.parametrize("strategy", ["basic", "by_title"])
@pytest.mark.parametrize("include_orig_elements", [False, True])
def test_partition_audio_chunks_keep_the_range_of_the_transcribed_segments(
    strategy, include_orig_elements, tmp_path, monkeypatch
):
    path = tmp_path / "recording.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 8000)

    class Agent:
        def transcribe_segments(self, audio_path, language=None):
            with wave.open(audio_path) as wav:
                assert wav.getnframes() == 8000
            return [
                {"text": "First retained transcript segment.", "start": 2.0, "end": 4.0},
                {"text": "Second retained transcript segment.", "start": 0.0, "end": 1.5},
                {"text": "  ", "start": 10.0, "end": 20.0},
                {"text": "Final retained transcript segment.", "start": 4.5, "end": 8.0},
            ]

    monkeypatch.setattr(
        "unstructured.partition.audio.SpeechToTextAgent.get_agent", lambda _: Agent()
    )
    chunks = partition_audio(
        filename=str(path),
        chunking_strategy=strategy,
        max_characters=1000,
        include_orig_elements=include_orig_elements,
    )

    assert len(chunks) == 1
    assert chunks[0].metadata.segment_start_seconds == 0.0
    assert chunks[0].metadata.segment_end_seconds == 8.0
    assert "First retained" in chunks[0].text
    assert "Final retained" in chunks[0].text
    assert (chunks[0].metadata.orig_elements is not None) == include_orig_elements


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize("max_characters", [16, 1000])
def test_splitting_one_segment_retains_its_whole_source_interval(chunk, max_characters):
    source = NarrativeText(
        "A long transcript segment contains words that may span several text chunks.",
        metadata=ElementMetadata(segment_start_seconds=3.25, segment_end_seconds=8.75),
    )

    chunks = chunk([source], max_characters=max_characters, include_orig_elements=False)

    assert bool(len(chunks) > 1) == (max_characters == 16)
    assert all(item.metadata.segment_start_seconds == 3.25 for item in chunks)
    assert all(item.metadata.segment_end_seconds == 8.75 for item in chunks)
    assert source.metadata.segment_start_seconds == 3.25
    assert source.metadata.segment_end_seconds == 8.75


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
@pytest.mark.parametrize(("start", "end"), [(None, None), (0.0, 0.0), (0.0, None), (None, 8.0)])
def test_chunk_ranges_preserve_zero_and_absent_timestamp_fields(chunk, start, end):
    elements = [
        Text("An untimed introduction."),
        NarrativeText(
            "The transcript segment.",
            metadata=ElementMetadata(segment_start_seconds=start, segment_end_seconds=end),
        ),
    ]

    result = chunk(elements, max_characters=1000)[0].metadata

    assert result.segment_start_seconds == start
    assert result.segment_end_seconds == end


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
def test_each_chunk_uses_only_its_own_segments(chunk):
    elements = [
        NarrativeText(
            text,
            metadata=ElementMetadata(segment_start_seconds=start, segment_end_seconds=end),
        )
        for text, start, end in [("alpha " * 5, 0.0, 2.0), ("bravo " * 5, 5.0, 7.0)]
    ]

    chunks = chunk(elements, max_characters=40)

    assert len(chunks) == 2
    assert [
        (item.metadata.segment_start_seconds, item.metadata.segment_end_seconds) for item in chunks
    ] == [(0.0, 2.0), (5.0, 7.0)]


@pytest.mark.parametrize("chunk", [chunk_elements, chunk_by_title])
def test_timestamp_aggregation_is_supported_in_metadata_only_image_runs(chunk):
    elements = [
        Image("", metadata=ElementMetadata(segment_start_seconds=3.0, segment_end_seconds=5.0)),
        Image("", metadata=ElementMetadata(segment_start_seconds=0.0, segment_end_seconds=8.0)),
        NarrativeText("A transcript with associated frames."),
    ]

    result = chunk(elements, max_characters=1000, include_orig_elements=False)[0].metadata

    assert result.segment_start_seconds == 0.0
    assert result.segment_end_seconds == 8.0
