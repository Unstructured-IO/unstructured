import os
import pytest

import docx

import unstructured.file_utils.metadata as meta


def test_get_docx_metadata_from_filename(tmpdir):
    filename = os.path.join(tmpdir, "test-doc.docx")

    document = docx.Document()
    document.add_paragraph("Lorem ipsum dolor sit amet.")
    document.core_properties.author = "Mr. Miagi"
    document.save(filename)

    metadata = meta.get_docx_metadata(filename=filename)
    assert metadata["author"] == "Mr. Miagi"


def test_get_docx_metadata_from_file(tmpdir):
    filename = os.path.join(tmpdir, "test-doc.docx")

    document = docx.Document()
    document.add_paragraph("Lorem ipsum dolor sit amet.")
    document.core_properties.author = "Mr. Miagi"
    document.save(filename)

    with open(filename, "rb") as f:
        metadata = meta.get_docx_metadata(file=f)
    assert metadata["author"] == "Mr. Miagi"


def test_get_docx_metadata_raises_without_file_or_filename():
    with pytest.raises(FileNotFoundError):
        meta.get_docx_metadata()
