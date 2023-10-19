from unstructured.partition.audio import partition_audio
from unstructured.documents.elements import AudioSegment
import pytest
import os
import pathlib

DIRECTORY = pathlib.Path(__file__).parent.resolve()

EXPECTED_OUTPUT = [
    AudioSegment(text=' With the explosion of large language models such as GPT-4,'),
]