"""Recover readable MIME text when its optional charset name is unknown."""

import email
import email.policy
import io
from email.message import EmailMessage

import pytest

from unstructured.partition.email import (
    EmailPartitioningContext,
    _AttachmentPartitioner,
    partition_email,
)


@pytest.mark.parametrize("subtype", ["plain", "html"])
@pytest.mark.parametrize("cte", ["8bit", "base64", "quoted-printable"])
def test_unknown_body_charset_recovers_utf8_content(subtype, cte):
    message = EmailMessage()
    message["From"] = "alice@example.invalid"
    message["To"] = "bob@example.invalid"
    message["Subject"] = "Preserved subject"
    body = "Résumé — café" if subtype == "plain" else "<h1>Résumé — café</h1>"
    message.set_content(body, subtype=subtype, charset="utf-8", cte=cte)
    message.set_param("charset", "unknown-vendor-encoding", replace=True)

    elements = partition_email(
        file=io.BytesIO(message.as_bytes()), process_attachments=False, languages=["fra"]
    )

    assert [element.text for element in elements] == ["Résumé — café"]
    assert elements[0].metadata.subject == "Preserved subject"
    assert elements[0].metadata.sent_from == ["alice@example.invalid"]
    assert elements[0].metadata.sent_to == ["bob@example.invalid"]


@pytest.mark.parametrize("cte", ["8bit", "base64", "quoted-printable"])
def test_unknown_charset_in_a_text_attachment_preserves_decoded_bytes(cte):
    attachment = EmailMessage()
    attachment.set_content("Résumé — café", charset="utf-8", cte=cte)
    attachment.add_header("Content-Disposition", "attachment", filename="note.txt")
    attachment.set_param("charset", "unknown-vendor-encoding", replace=True)
    parsed = email.message_from_bytes(attachment.as_bytes(), policy=email.policy.default)

    partitioner = _AttachmentPartitioner(parsed, EmailPartitioningContext())

    assert partitioner._file_bytes.decode("utf-8") == "Résumé — café\n"
    assert parsed.get_content_charset() == "unknown-vendor-encoding"


@pytest.mark.parametrize("charset", ["utf-8", "iso-8859-1"])
def test_valid_declared_charset_keeps_its_existing_decoding(charset):
    message = EmailMessage()
    message.set_content("Résumé café", charset=charset, cte="base64")

    elements = partition_email(
        file=io.BytesIO(message.as_bytes()), process_attachments=False, languages=["fra"]
    )

    assert [element.text for element in elements] == ["Résumé café"]


def test_binary_attachment_is_not_decoded_as_text():
    attachment = EmailMessage()
    payload = b"\x00\xff\x80\r\n\x01"
    attachment.set_content(payload, maintype="application", subtype="octet-stream")
    parsed = email.message_from_bytes(attachment.as_bytes(), policy=email.policy.default)

    assert _AttachmentPartitioner(parsed, EmailPartitioningContext())._file_bytes == payload
