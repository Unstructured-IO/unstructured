"""Keep the immediate containing message when email attachments contain other attachments."""

from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

import pytest
from oxmsg.attachment import Attachment

from test_unstructured.unit_utils import example_doc_path
from unstructured.documents.elements import Element
from unstructured.partition.auto import partition
from unstructured.partition.email import partition_email
from unstructured.partition.msg import partition_msg

OUTER_TEXT = "This is the outer message body."
MIDDLE_TEXT = "This is the middle message body."
INNER_TEXT = "This is the innermost message body."
LEAF_TEXT = "This document belongs to the innermost message."
DIRECT_TEXT = "This document belongs directly to the outer message."


def _message(subject: str, body: str) -> EmailMessage:
    """Build a real MIME message with recognizable email headers."""
    message = EmailMessage()
    message["From"] = "sender@example.com"
    message["To"] = "recipient@example.com"
    message["Subject"] = subject
    message.set_content(body)
    return message


def _inner_message() -> EmailMessage:
    """Build an attached email that itself has a plain-text attachment."""
    message = _message("Inner message", INNER_TEXT)
    message.add_attachment(LEAF_TEXT, filename="leaf.txt")
    return message


def _by_text(elements: list[Element]) -> dict[str, Element]:
    """Find each unique body or attachment independently of element classification."""
    return {str(element): element for element in elements}


@pytest.mark.parametrize("via_auto", [False, True])
@pytest.mark.parametrize("outer_filename", [None, "mail/outer.eml"])
@pytest.mark.parametrize("inner_filename", [None, "inner.eml"])
@pytest.mark.parametrize("depth", [2, 3])
def test_eml_nested_attachments_keep_their_immediate_parent(
    via_auto: bool, outer_filename: str | None, inner_filename: str | None, depth: int
) -> None:
    outer = _message("Outer message", OUTER_TEXT)
    if depth == 3:
        middle = _message("Middle message", MIDDLE_TEXT)
        middle.add_attachment(_inner_message(), filename=inner_filename)
        outer.add_attachment(middle, filename="middle.eml")
    else:
        outer.add_attachment(_inner_message(), filename=inner_filename)
    outer.add_attachment(DIRECT_TEXT, filename="direct.txt")

    partitioner = partition if via_auto else partition_email
    elements = partitioner(
        file=BytesIO(outer.as_bytes()),
        metadata_filename=outer_filename,
        languages=["eng"],
    )

    by_text = _by_text(elements)
    outer_name = "outer.eml" if outer_filename else None
    assert len(elements) == (5 if depth == 3 else 4)
    assert by_text[OUTER_TEXT].metadata.attached_to_filename is None
    assert by_text[DIRECT_TEXT].metadata.attached_to_filename == outer_name
    assert by_text[INNER_TEXT].metadata.attached_to_filename == (
        "middle.eml" if depth == 3 else outer_name
    )
    assert by_text[INNER_TEXT].metadata.filename == inner_filename
    assert by_text[INNER_TEXT].metadata.subject == "Inner message"
    assert by_text[INNER_TEXT].metadata.filetype == "message/rfc822"
    assert by_text[LEAF_TEXT].metadata.attached_to_filename == inner_filename
    assert by_text[LEAF_TEXT].metadata.filename == "leaf.txt"
    assert by_text[LEAF_TEXT].metadata.filetype == "text/plain"
    if depth == 3:
        assert by_text[MIDDLE_TEXT].metadata.attached_to_filename == outer_name
        assert by_text[MIDDLE_TEXT].metadata.filename == "middle.eml"


@pytest.mark.parametrize("via_auto", [False, True])
@pytest.mark.parametrize("outer_filename", [None, "outer.eml"])
def test_eml_keeps_the_parent_of_an_attachment_inside_a_real_msg(
    via_auto: bool, outer_filename: str | None
) -> None:
    outer = _message("Outer message", OUTER_TEXT)
    outer.add_attachment(
        Path(example_doc_path("fake-email-attachment.msg")).read_bytes(),
        maintype="application",
        subtype="vnd.ms-outlook",
        filename="inner.msg",
    )

    partitioner = partition if via_auto else partition_email
    elements = partitioner(
        file=BytesIO(outer.as_bytes()),
        metadata_filename=outer_filename,
        languages=["eng"],
    )

    attachment_elements = [e for e in elements if e.metadata.filename == "fake-attachment.txt"]
    assert len(attachment_elements) == 1
    assert str(attachment_elements[0]) == "Hey this is a fake attachment!"
    assert attachment_elements[0].metadata.attached_to_filename == "inner.msg"
    assert attachment_elements[0].metadata.filetype == "text/plain"
    msg_body = [e for e in elements if e.metadata.filename == "inner.msg"]
    assert msg_body
    assert all(e.metadata.attached_to_filename == outer_filename for e in msg_body)
    assert all(e.metadata.filetype == "application/vnd.ms-outlook" for e in msg_body)


@pytest.mark.parametrize("via_auto", [False, True])
@pytest.mark.parametrize("outer_filename", [None, "mail/outer.msg"])
@pytest.mark.parametrize("inner_filename", [None, "inner.eml"])
def test_msg_keeps_the_parents_inside_an_attached_eml(
    via_auto: bool,
    outer_filename: str | None,
    inner_filename: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    middle = _message("Middle message", MIDDLE_TEXT)
    middle.add_attachment(_inner_message(), filename=inner_filename)
    attachment_bytes = middle.as_bytes()
    # Supply nested MIME content through the real MSG reader's attachment properties. The MSG
    # body, attachment dispatch, nested EML parsing, and final text partitioning all run normally.
    monkeypatch.setattr(Attachment, "file_name", property(lambda self: "middle.eml"))
    monkeypatch.setattr(Attachment, "file_bytes", property(lambda self: attachment_bytes))
    source = Path(example_doc_path("fake-email-attachment.msg")).read_bytes()

    partitioner = partition if via_auto else partition_msg
    elements = partitioner(
        file=BytesIO(source),
        metadata_filename=outer_filename,
        languages=["eng"],
    )

    by_text = _by_text(elements)
    assert by_text[MIDDLE_TEXT].metadata.attached_to_filename == outer_filename
    assert by_text[MIDDLE_TEXT].metadata.filename == "middle.eml"
    assert by_text[INNER_TEXT].metadata.attached_to_filename == "middle.eml"
    assert by_text[INNER_TEXT].metadata.filename == inner_filename
    assert by_text[LEAF_TEXT].metadata.attached_to_filename == inner_filename
    assert by_text[LEAF_TEXT].metadata.filename == "leaf.txt"
    assert by_text[LEAF_TEXT].metadata.filetype == "text/plain"
