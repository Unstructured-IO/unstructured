from __future__ import annotations

from os import PathLike
from typing import Protocol, TypeVar

from typing_extensions import TypeAlias

AnyStr_cov = TypeVar("AnyStr_cov", str, bytes, covariant=True)
FilePath: TypeAlias = str | PathLike[str]
S1 = TypeVar("S1")

class BaseBuffer(Protocol):
    @property
    def mode(self) -> str: ...
    def seek(self, __offset: int, __whence: int = ...) -> int: ...
    def seekable(self) -> bool: ...
    def tell(self) -> int: ...

class ReadBuffer(BaseBuffer, Protocol[AnyStr_cov]):
    def read(self, __n: int = ...) -> AnyStr_cov: ...
