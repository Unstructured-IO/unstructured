from unstructured.ingest.pipeline.encrypt.interfaces import Encryption


class NoopEncryption(Encryption):
    def encrypt(self, s: str) -> str:
        return s

    def decrypt(self, s: str) -> str:
        return s
