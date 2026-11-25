"""MSG attachments are documents, independent of local temporary-file naming limits."""

import tempfile

import pytest
from oxmsg.attachment import Attachment

from test_unstructured.unit_utils import example_doc_path
from unstructured.partition.auto import partition
from unstructured.partition.msg import partition_msg


@pytest.mark.parametrize(
    "attachment_name",
    ["report.txt", "a" * 300 + ".txt", "报表" * 60 + ".txt"],
)
def test_partition_msg_accepts_attachment_names_beyond_local_filename_limits(
    attachment_name: str, monkeypatch: pytest.MonkeyPatch
):
    """A real MSG attachment keeps its text and name without requiring a filesystem path."""
    monkeypatch.setattr(Attachment, "file_name", property(lambda self: attachment_name))

    elements = partition_msg(example_doc_path("fake-email-attachment.msg"))

    attachment_elements = [e for e in elements if e.metadata.attached_to_filename]
    assert len(attachment_elements) == 1
    element = attachment_elements[0]
    assert element.text == "Hey this is a fake attachment!"
    assert element.metadata.filename == attachment_name
    assert element.metadata.filetype == "text/plain"
    assert element.metadata.last_modified == "2023-04-20T21:39:10+00:00"


def test_partition_msg_does_not_require_a_temporary_directory_for_a_text_attachment(
    monkeypatch: pytest.MonkeyPatch,
):
    """An already-loaded attachment can still be read when temporary storage is unavailable."""

    def unavailable_directory(*args, **kwargs):
        """Model a worker with no writable temporary storage."""
        raise OSError("temporary storage unavailable")

    monkeypatch.setattr(tempfile, "TemporaryDirectory", unavailable_directory)

    elements = partition_msg(example_doc_path("fake-email-attachment.msg"))

    attachment_elements = [e for e in elements if e.metadata.attached_to_filename]
    assert [e.text for e in attachment_elements] == ["Hey this is a fake attachment!"]


def test_partition_msg_keeps_sanitized_attachment_filename_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    """Removing filesystem writes does not remove the existing metadata filename sanitizer."""
    monkeypatch.setattr(Attachment, "file_name", property(lambda self: r"..\private/../report.txt"))

    elements = partition_msg(example_doc_path("fake-email-attachment.msg"))

    attachment_elements = [e for e in elements if e.metadata.attached_to_filename]
    assert [e.metadata.filename for e in attachment_elements] == ["report.txt"]
    assert [e.text for e in attachment_elements] == ["Hey this is a fake attachment!"]


@pytest.mark.parametrize(
    ("filename", "dependency"),
    [
        ("fake.docx", "docx"),
        ("fake-power-point-table.pptx", "pptx"),
        ("stanley-cups.csv", "pandas"),
        ("stanley-cups.tsv", "pandas"),
        ("stanley-cups.xlsx", "openpyxl"),
    ],
)
def test_partition_msg_attachment_content_matches_the_standalone_document(
    filename: str, dependency: str, monkeypatch: pytest.MonkeyPatch
):
    """Actual office and table document delegates preserve extraction when given a stream."""
    pytest.importorskip(dependency)
    path = example_doc_path(filename)
    with open(path, "rb") as file:
        attachment_bytes = file.read()
    monkeypatch.setattr(Attachment, "file_name", property(lambda self: filename))
    monkeypatch.setattr(Attachment, "file_bytes", property(lambda self: attachment_bytes))

    elements = partition_msg(example_doc_path("fake-email-attachment.msg"))
    attachment_elements = [e for e in elements if e.metadata.attached_to_filename]
    standalone_elements = partition(path)

    assert attachment_elements
    assert [
        (e.category, e.text, e.metadata.text_as_html, e.metadata.filetype)
        for e in attachment_elements
    ] == [
        (e.category, e.text, e.metadata.text_as_html, e.metadata.filetype)
        for e in standalone_elements
    ]
    assert all(e.metadata.filename == filename for e in attachment_elements)
