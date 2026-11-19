import io
import os
from pathlib import Path

import pytest

from unstructured.partition.common.metadata import get_last_modified_date
from unstructured.partition.email import partition_email

BAD_DATES = [
    "Fri, 31 Dec 9999 23:59:59 -0100",
    "0001-01-01T00:00:00+01:00",
    "Fri, 01 Jan 99999999999999999999 12:00:00 +0000",
]
BODY = "The complete email body must remain available."


def email_bytes(date: str) -> bytes:
    return (
        f"From: sender@example.com\nTo: reader@example.com\nDate: {date}\n"
        f"Subject: Date metadata\nContent-Type: text/plain; charset=utf-8\n\n{BODY}\n"
    ).encode()


@pytest.mark.parametrize("date", [*BAD_DATES, "not a date"])
@pytest.mark.parametrize("source", ["filename", "stream"])
def test_unrepresentable_email_date_keeps_body_and_uses_metadata_fallback(
    date: str, source: str, tmp_path: Path
):
    path = tmp_path / "message.eml"
    path.write_bytes(email_bytes(date))
    os.utime(path, (1_700_000_000, 1_700_000_000))
    kwargs = (
        {"filename": str(path)} if source == "filename" else {"file": io.BytesIO(path.read_bytes())}
    )

    elements = partition_email(**kwargs, process_attachments=False)

    assert [element.text for element in elements] == [BODY]
    expected_date = get_last_modified_date(str(path)) if source == "filename" else None
    assert elements[0].metadata.last_modified == expected_date
    assert elements[0].metadata.subject == "Date metadata"
    assert elements[0].metadata.sent_from == ["sender@example.com"]


@pytest.mark.parametrize("date", BAD_DATES)
def test_explicit_email_metadata_date_still_takes_precedence(date: str):
    override = "2026-01-02T03:04:05+00:00"
    elements = partition_email(
        file=io.BytesIO(email_bytes(date)),
        metadata_last_modified=override,
        process_attachments=False,
    )
    assert elements[0].metadata.last_modified == override
    assert elements[0].text == BODY


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        ("Fri, 31 Dec 9999 23:59:59 +0000", "9999-12-31T23:59:59+00:00"),
        ("0001-01-01T00:00:00+00:00", "0001-01-01T00:00:00+00:00"),
        ("Fri, 01 Jan 2021 12:00:00 +0530", "2021-01-01T06:30:00+00:00"),
        ("Fri, 01 Jan 2021 12:00:00 -0800", "2021-01-01T20:00:00+00:00"),
    ],
)
def test_representable_email_dates_keep_their_existing_utc_values(date: str, expected: str):
    elements = partition_email(file=io.BytesIO(email_bytes(date)), process_attachments=False)
    assert elements[0].metadata.last_modified == expected
    assert elements[0].text == BODY
