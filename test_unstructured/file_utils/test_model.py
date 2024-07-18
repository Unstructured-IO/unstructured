"""Test suite for `unstructured.file_utils.filetype`."""

from __future__ import annotations

import pytest

from unstructured.file_utils.model import FileType


class DescribeFileType:
    """Unit-test suite for `unstructured.file_utils.model.Filetype`."""

    @pytest.mark.parametrize(
        ("ext", "file_type"),
        [
            (".bmp", FileType.BMP),
            (".html", FileType.HTML),
            (".eml", FileType.EML),
            (".p7s", FileType.EML),
            (".java", FileType.TXT),
        ],
    )
    def it_can_recognize_a_file_type_from_an_extension(self, ext: str, file_type: FileType | None):
        assert FileType.from_extension(ext) is file_type

    @pytest.mark.parametrize("ext", [".foobar", ".xyz", ".mdx", "", "."])
    def but_not_when_that_extension_is_empty_or_not_registered(self, ext: str):
        assert FileType.from_extension(ext) is None

    @pytest.mark.parametrize(
        ("mime_type", "file_type"),
        [
            ("image/bmp", FileType.BMP),
            ("text/x-csv", FileType.CSV),
            ("application/msword", FileType.DOC),
            ("message/rfc822", FileType.EML),
            ("text/plain", FileType.TXT),
            ("text/yaml", FileType.TXT),
            ("application/xml", FileType.XML),
            ("text/xml", FileType.XML),
            ("inode/x-empty", FileType.EMPTY),
        ],
    )
    def it_can_recognize_a_file_type_from_a_mime_type(
        self, mime_type: str, file_type: FileType | None
    ):
        assert FileType.from_mime_type(mime_type) is file_type

    @pytest.mark.parametrize("mime_type", ["text/css", "image/gif", "audio/mpeg", "foo/bar"])
    def but_not_when_that_mime_type_is_not_registered_by_a_file_type(self, mime_type: str):
        assert FileType.from_mime_type(mime_type) is None

    @pytest.mark.parametrize(
        ("file_type", "mime_type"),
        [
            (FileType.BMP, "image/bmp"),
            (FileType.CSV, "text/csv"),
            (FileType.DOC, "application/msword"),
            (FileType.EML, "message/rfc822"),
            (FileType.HTML, "text/html"),
            (FileType.JPG, "image/jpeg"),
            (FileType.PDF, "application/pdf"),
            (FileType.TXT, "text/plain"),
            (FileType.XML, "application/xml"),
            (FileType.EMPTY, "inode/x-empty"),
            (FileType.UNK, "application/octet-stream"),
        ],
    )
    def it_knows_its_canonical_MIME_type(self, file_type: FileType, mime_type: str):
        assert file_type.mime_type == mime_type
