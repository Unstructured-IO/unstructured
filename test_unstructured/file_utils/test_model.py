"""Test suite for `unstructured.file_utils.filetype`."""

from __future__ import annotations

import pytest

from unstructured.file_utils.model import FileType, create_file_type, register_partitioner


class DescribeFileType:
    """Unit-test suite for `unstructured.file_utils.model.Filetype`."""

    # -- .__lt__() ----------------------------------------------

    def it_is_a_collection_ordered_by_name_and_can_be_sorted(self):
        """FileType is a total order on name, e.g. FileType.A < FileType.B."""
        assert FileType.EML < FileType.HTML < FileType.XML

    # -- .from_extension() --------------------------------------

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

    @pytest.mark.parametrize("ext", [".foobar", ".xyz", ".mdx", "", ".", None])
    def but_not_when_that_extension_is_empty_or_None_or_not_registered(self, ext: str | None):
        assert FileType.from_extension(ext) is None

    # -- .from_mime_type() --------------------------------------

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

    @pytest.mark.parametrize("mime_type", ["text/css", "image/gif", "audio/mpeg", "foo/bar", None])
    def but_not_when_that_mime_type_is_not_registered_by_a_file_type_or_None(
        self, mime_type: str | None
    ):
        assert FileType.from_mime_type(mime_type) is None

    # -- .extra_name --------------------------------------------

    @pytest.mark.parametrize(
        ("file_type", "expected_value"),
        [
            (FileType.BMP, "image"),
            (FileType.DOC, "doc"),
            (FileType.DOCX, "docx"),
            (FileType.EML, None),
            (FileType.EMPTY, None),
            (FileType.MSG, "msg"),
            (FileType.PDF, "pdf"),
            (FileType.XLS, "xlsx"),
            (FileType.UNK, None),
            (FileType.WAV, None),
            (FileType.ZIP, None),
        ],
    )
    def and_it_knows_which_pip_extra_needs_to_be_installed_to_get_those_dependencies(
        self, file_type: FileType, expected_value: str | None
    ):
        assert file_type.extra_name == expected_value

    # -- .importable_package_dependencies -----------------------

    @pytest.mark.parametrize(
        ("file_type", "expected_value"),
        [
            (FileType.BMP, ("unstructured_inference",)),
            (FileType.CSV, ("pandas",)),
            (FileType.DOC, ("docx",)),
            (FileType.EMPTY, ()),
            (FileType.HTML, ()),
            (FileType.ODT, ("docx", "pypandoc")),
            (FileType.PDF, ("pdf2image", "pdfminer", "PIL")),
            (FileType.UNK, ()),
            (FileType.WAV, ()),
            (FileType.ZIP, ()),
        ],
    )
    def it_knows_which_importable_packages_its_partitioner_depends_on(
        self, file_type: FileType, expected_value: tuple[str, ...]
    ):
        assert file_type.importable_package_dependencies == expected_value

    # -- .is_partitionable --------------------------------------

    @pytest.mark.parametrize(
        ("file_type", "expected_value"),
        [
            (FileType.BMP, True),
            (FileType.CSV, True),
            (FileType.DOC, True),
            (FileType.EML, True),
            (FileType.JPG, True),
            (FileType.PDF, True),
            (FileType.PPTX, True),
            (FileType.WAV, False),
            (FileType.ZIP, False),
            (FileType.EMPTY, False),
            (FileType.UNK, False),
        ],
    )
    def it_knows_whether_files_of_its_type_are_directly_partitionable(
        self, file_type: FileType, expected_value: str
    ):
        assert file_type.is_partitionable is expected_value

    # -- .mime_type ---------------------------------------------

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

    # -- .partitioner_function_name -----------------------------

    @pytest.mark.parametrize(
        ("file_type", "expected_value"),
        [
            (FileType.BMP, "partition_image"),
            (FileType.CSV, "partition_csv"),
            (FileType.DOC, "partition_doc"),
            (FileType.DOCX, "partition_docx"),
            (FileType.JPG, "partition_image"),
            (FileType.PNG, "partition_image"),
            (FileType.TIFF, "partition_image"),
        ],
    )
    def it_knows_its_partitioner_function_name(self, file_type: FileType, expected_value: str):
        assert file_type.partitioner_function_name == expected_value

    @pytest.mark.parametrize(
        "file_type", [FileType.WAV, FileType.ZIP, FileType.EMPTY, FileType.UNK]
    )
    def but_it_raises_on_partitioner_function_name_access_when_the_file_type_is_not_partitionable(
        self, file_type: FileType
    ):
        with pytest.raises(ValueError, match="`.partitioner_function_name` is undefined because "):
            file_type.partitioner_function_name

    # -- .partitioner_module_qname ------------------------------

    @pytest.mark.parametrize(
        ("file_type", "expected_value"),
        [
            (FileType.BMP, "unstructured.partition.image"),
            (FileType.CSV, "unstructured.partition.csv"),
            (FileType.DOC, "unstructured.partition.doc"),
            (FileType.DOCX, "unstructured.partition.docx"),
            (FileType.JPG, "unstructured.partition.image"),
            (FileType.PNG, "unstructured.partition.image"),
            (FileType.TIFF, "unstructured.partition.image"),
        ],
    )
    def it_knows_the_fully_qualified_name_of_its_partitioner_module(
        self, file_type: FileType, expected_value: str
    ):
        assert file_type.partitioner_module_qname == expected_value

    @pytest.mark.parametrize(
        "file_type", [FileType.WAV, FileType.ZIP, FileType.EMPTY, FileType.UNK]
    )
    def but_it_raises_on_partitioner_module_qname_access_when_the_file_type_is_not_partitionable(
        self, file_type: FileType
    ):
        with pytest.raises(ValueError, match="`.partitioner_module_qname` is undefined because "):
            file_type.partitioner_module_qname

    # -- .partitioner_shortname ---------------------------------

    @pytest.mark.parametrize(
        ("file_type", "expected_value"),
        [
            (FileType.BMP, "image"),
            (FileType.CSV, "csv"),
            (FileType.DOC, "doc"),
            (FileType.DOCX, "docx"),
            (FileType.JPG, "image"),
            (FileType.PNG, "image"),
            (FileType.TIFF, "image"),
            (FileType.XLS, "xlsx"),
            (FileType.XLSX, "xlsx"),
        ],
    )
    def it_provides_access_to_the_partitioner_shortname(
        self, file_type: FileType, expected_value: str
    ):
        assert file_type.partitioner_shortname == expected_value


def test_create_file_type():
    file_type = create_file_type("FOO", canonical_mime_type="application/foo", extensions=[".foo"])

    assert FileType.from_extension(".foo") is file_type
    assert FileType.from_mime_type("application/foo") is file_type


def test_register_partitioner():
    file_type = create_file_type("FOO", canonical_mime_type="application/foo", extensions=[".foo"])

    @register_partitioner(file_type)
    def partition_foo():
        pass

    assert file_type.partitioner_function_name == "partition_foo"
    assert file_type.partitioner_module_qname == "test_unstructured.file_utils.test_model"
