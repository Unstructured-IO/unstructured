from dataclasses import dataclass

from cryptography.fernet import Fernet

from unstructured.ingest.pipeline.encrypt.interfaces import Encryption


@dataclass
class FernetEncryption(Encryption):
    key: str
    encoding: str = "UTF-8"

    def __post_init__(self):
        self.fernet = Fernet(self.key)

    def encrypt(self, s: str) -> str:
        return self.fernet.encrypt(s.encode()).decode()

    def decrypt(self, s: str) -> str:
        return self.fernet.decrypt(s.encode()).decode()
