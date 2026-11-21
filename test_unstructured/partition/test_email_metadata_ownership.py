import io
from email.message import EmailMessage
from types import SimpleNamespace

import pytest

from unstructured.documents.elements import ElementMetadata, Text
from unstructured.partition.email import partition_email
from unstructured.partition.msg import _MsgPartitioner


@pytest.mark.parametrize("field", ["sent_from", "sent_to", "cc_recipient", "bcc_recipient"])
def test_eml_elements_own_their_address_lists(field):
    message = EmailMessage()
    message["From"] = "Sender <sender@example.com>"
    message["To"] = "recipient@example.com"
    message["Cc"] = "copy@example.com"
    message["Bcc"] = "private@example.com"
    message.set_content("First paragraph.\n\nSecond paragraph.")

    elements = partition_email(
        file=io.BytesIO(message.as_bytes()), process_attachments=False, languages=["eng"]
    )

    assert len(elements) == 2
    original = getattr(elements[1].metadata, field).copy()
    getattr(elements[0].metadata, field).clear()
    assert getattr(elements[1].metadata, field) == original


def test_msg_elements_and_context_own_their_address_lists(monkeypatch):
    from unstructured.partition import msg

    shared = ElementMetadata(sent_to=["recipient@example.com"], cc_recipient=["copy@example.com"])
    options = SimpleNamespace(
        msg=SimpleNamespace(html_body="<p>first</p><p>second</p>"),
        metadata_file_path=None,
        metadata_last_modified=None,
        partitioning_kwargs={},
        extra_msg_metadata=shared,
    )
    monkeypatch.setattr(msg, "partition_html", lambda **kwargs: [Text("first"), Text("second")])

    elements = list(_MsgPartitioner(options)._iter_message_body_elements())
    elements[0].metadata.sent_to.clear()
    elements[1].metadata.cc_recipient.append("other@example.com")

    assert elements[1].metadata.sent_to == ["recipient@example.com"]
    assert elements[0].metadata.cc_recipient == ["copy@example.com"]
    assert shared.sent_to == ["recipient@example.com"]
    assert shared.cc_recipient == ["copy@example.com"]
