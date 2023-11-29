from dataclasses import dataclass

from cryptography.fernet import Fernet

from unstructured.ingest.pipeline.encrypt.interfaces import Encryption


@dataclass
class FernetEncryption(Encryption):
    """
    To make it easier to work with strings rather than bytes, each method is
    responsible for encoding/decoding the bytes that the fernet library expects.
    """

    key: str
    encoding: str = "UTF-8"

    def __post_init__(self):
        self.fernet = Fernet(self.key)

    def encrypt(self, s: str) -> str:
        return self.fernet.encrypt(s.encode(encoding=self.encoding)).decode(encoding=self.encoding)

    def decrypt(self, s: str) -> str:
        return self.fernet.decrypt(s.encode(encoding=self.encoding)).decode(encoding=self.encoding)
