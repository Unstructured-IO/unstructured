from enum import Enum
import os
from typing import IO, Optional
from file_utils import _detect_filetype_from_extension
from unstructured.file_utils.filetype import FileType
import zipfile

def test_detect_filetype_from_extension():
    assert _detect_filetype_from_extension('.txt') == FileType.TEXT
    assert _detect_filetype_from_extension('.text') == FileType.TEXT
    assert _detect_filetype_from_extension('.pdf') == FileType.PDF
    assert _detect_filetype_from_extension('.jpg') == FileType.IMAGE
    assert _detect_filetype_from_extension('.jpeg') == FileType.IMAGE
    assert _detect_filetype_from_extension('.png') == FileType.IMAGE
    assert _detect_filetype_from_extension('.gif') == FileType.IMAGE
    assert _detect_filetype_from_extension('.mp3') is None
    # Add more test cases for other file types.
