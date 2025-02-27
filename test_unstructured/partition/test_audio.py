# pyright: reportPrivateUsage=false

"""Test-suite for the `unstructured.partition.audio` module."""

from unstructured.partition.audio import (
    partition_audio,
)

def test_partition_audio_from_filename():
    elements = partition_audio("example-docs/audio/test.mp3")
    assert len(elements) == 6
