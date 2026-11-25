"""Outlook recipient-table roles determine the destination metadata fields."""

import pytest
from oxmsg import Message
from oxmsg.domain.constants import PID_RECIPIENT_TYPE
from oxmsg.properties import Properties

from test_unstructured.unit_utils import example_doc_path
from unstructured.partition.msg import MsgPartitionerOptions, partition_msg


@pytest.fixture
def opts() -> MsgPartitionerOptions:
    """Read the existing MSG fixture containing one To, one Cc, and one Bcc recipient."""
    return MsgPartitionerOptions(
        file=None,
        file_path=example_doc_path("fake-email-with-cc-and-bcc.msg"),
        metadata_file_path=None,
        metadata_last_modified=None,
        partition_attachments=False,
        kwargs={},
    )


def test_partition_msg_separates_primary_copy_and_blind_copy_recipients():
    """The public partitioner does not classify Cc and Bcc addresses as primary recipients."""
    elements = partition_msg(
        example_doc_path("fake-email-with-cc-and-bcc.msg"), process_attachments=False
    )

    assert elements
    for element in elements:
        assert element.metadata.sent_to == ["john-ctr@unstructured.io"]
        assert element.metadata.cc_recipient == ["steve@unstructured.io"]
        assert element.metadata.bcc_recipient == ["hello@unstructured.io"]


@pytest.mark.parametrize("submitted_flag", [0, 0x80000000])
def test_msg_recipient_table_supplies_roles_when_transport_headers_are_missing(
    submitted_flag: int, opts: MsgPartitionerOptions, monkeypatch: pytest.MonkeyPatch
):
    """Recipients survive absent transport headers, including the MAPI_SUBMITTED flag."""
    monkeypatch.setattr(Message, "message_headers", property(lambda self: {}))
    original_int_prop_value = Properties.int_prop_value

    def int_prop_value(self: Properties, pid: int) -> int | None:
        """Mark the real fixture's recipients as previously submitted when requested."""
        value = original_int_prop_value(self, pid)
        if pid == PID_RECIPIENT_TYPE and value is not None:
            return value | submitted_flag
        return value

    monkeypatch.setattr(Properties, "int_prop_value", int_prop_value)

    metadata = opts.extra_msg_metadata

    assert metadata.sent_to == ["john-ctr@unstructured.io"]
    assert metadata.cc_recipient == ["steve@unstructured.io"]
    assert metadata.bcc_recipient == ["hello@unstructured.io"]


def test_msg_without_primary_recipients_has_no_sent_to(
    opts: MsgPartitionerOptions, monkeypatch: pytest.MonkeyPatch
):
    """A message addressed only to copied recipients has an empty primary-recipient field."""
    monkeypatch.setattr(Message, "message_headers", property(lambda self: {}))
    original_int_prop_value = Properties.int_prop_value

    def int_prop_value(self: Properties, pid: int) -> int | None:
        """Make the real fixture's primary recipient a copied recipient."""
        value = original_int_prop_value(self, pid)
        return 2 if pid == PID_RECIPIENT_TYPE and value == 1 else value

    monkeypatch.setattr(Properties, "int_prop_value", int_prop_value)

    metadata = opts.extra_msg_metadata

    assert metadata.sent_to is None
    assert metadata.cc_recipient == ["john-ctr@unstructured.io", "steve@unstructured.io"]
    assert metadata.bcc_recipient == ["hello@unstructured.io"]


def test_msg_missing_recipient_type_retains_legacy_primary_recipient_behavior(
    opts: MsgPartitionerOptions, monkeypatch: pytest.MonkeyPatch
):
    """Incomplete MSG records retain the previous primary-recipient fallback."""
    original_int_prop_value = Properties.int_prop_value

    def int_prop_value(self: Properties, pid: int) -> int | None:
        """Remove only the recipient-role property from the real fixture."""
        return None if pid == PID_RECIPIENT_TYPE else original_int_prop_value(self, pid)

    monkeypatch.setattr(Properties, "int_prop_value", int_prop_value)

    metadata = opts.extra_msg_metadata

    assert metadata.sent_to == [
        "john-ctr@unstructured.io",
        "steve@unstructured.io",
        "hello@unstructured.io",
    ]
    assert metadata.cc_recipient == ["steve@unstructured.io"]
    assert metadata.bcc_recipient == ["hello@unstructured.io"]
