import io
from email.message import EmailMessage

import pytest

from unstructured.partition.email import partition_email


@pytest.mark.parametrize("html", ["", " \n ", "<html><body></body></html>"])
def test_empty_preferred_html_does_not_hide_the_plain_body(html):
    message = EmailMessage()
    message["Subject"] = "Body fallback"
    message.set_content("The usable plain text body.")
    message.add_alternative(html, subtype="html")

    elements = partition_email(
        file=io.BytesIO(message.as_bytes()), process_attachments=False, languages=["eng"]
    )

    assert [e.text for e in elements] == ["The usable plain text body."]
    assert elements[0].metadata.subject == "Body fallback"


def test_empty_preferred_plain_text_falls_back_to_html():
    message = EmailMessage()
    message.set_content("")
    message.add_alternative("<p>The usable HTML body.</p>", subtype="html")

    elements = partition_email(
        file=io.BytesIO(message.as_bytes()),
        content_source="text/plain",
        process_attachments=False,
        languages=["eng"],
    )

    assert [e.text for e in elements] == ["The usable HTML body."]


def test_nonempty_preference_is_kept_and_alternatives_are_not_duplicated():
    message = EmailMessage()
    message.set_content("Plain body.")
    message.add_alternative("<p>HTML body.</p>", subtype="html")

    elements = partition_email(
        file=io.BytesIO(message.as_bytes()), process_attachments=False, languages=["eng"]
    )

    assert [e.text for e in elements] == ["HTML body."]
