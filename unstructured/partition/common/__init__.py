from typing import Final


class UnsupportedFileFormatError(Exception):
    """File-type is not supported for this operation.

    For example, when receiving a file for auto-partitioning where its file-formatt cannot be
    identified or there is no partitioner available for that file-format.
    """


# Exceptions that email/msg partitioners treat as "unsupported attachment" and skip with a
# warning (no data loss). Intentionally narrow: we do not catch RuntimeError (OOM, broken pipe,
# parser failures in e.g. pdfminer would otherwise be silently skipped).
EXPECTED_ATTACHMENT_ERRORS: Final[tuple[type[BaseException], ...]] = (
    UnsupportedFileFormatError,
    ImportError,
    FileNotFoundError,
)
