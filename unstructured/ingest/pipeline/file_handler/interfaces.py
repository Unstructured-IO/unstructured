import json
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from unstructured.ingest.pipeline.encrypt import Encryption, NoopEncryption

DEFAULT_ENCRYPTION = NoopEncryption()


@dataclass
class FileStat:
    exists: bool
    size: t.Optional[int] = None
    is_file: t.Optional[bool] = None


@dataclass
class FileHandler(ABC):
    def __post_init__(self):
        self.encryption: Encryption = DEFAULT_ENCRYPTION

    def set_encryption(self, encryption: Encryption):
        self.encryption = encryption

    @abstractmethod
    def cp(self, path1: str, path2: str, decrypt: bool = False):
        pass

    @abstractmethod
    def _write(self, data: str, filepath: str):
        pass

    @abstractmethod
    def _read(self, filepath: str) -> str:
        pass

    def write_json(self, data: t.Any, filepath: str, **json_dumps_kwargs):
        json_string = json.dumps(data, **json_dumps_kwargs)
        self.write(data=json_string, filepath=filepath)

    def read_json(self, filepath: str) -> dict:
        raw_data = self.read(filepath=filepath)
        return json.loads(raw_data)

    def write(self, data: str, filepath: str):
        encrypted_data = self.encryption.encrypt(data)
        self._write(data=encrypted_data, filepath=filepath)

    def read(self, filepath: str) -> str:
        encrypted_data = self._read(filepath=filepath)
        return self.encryption.decrypt(encrypted_data)

    @abstractmethod
    def stat(self, filepath: str) -> FileStat:
        pass
