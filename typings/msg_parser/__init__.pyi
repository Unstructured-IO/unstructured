from __future__ import annotations

from typing import Any

class MsOxMessage:
    attachments: list[Attachment]
    body: str | None
    header_dict: dict[str, Any]

    def __init__(self, msg_file_path: str) -> None: ...

class Attachment:
    AttachExtension: str | None
    AttachLongFilename: str | None
    AttachmentSize: int | None
    data: bytes
