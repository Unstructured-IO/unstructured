from abc import ABC, abstractmethod


class Encryption(ABC):
    @abstractmethod
    def encrypt(self, s: str) -> str:
        pass

    @abstractmethod
    def decrypt(self, s: str) -> str:
        pass
