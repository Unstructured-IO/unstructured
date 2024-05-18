class Table:
    @property
    def rows(self) -> tuple[_Row]: ...

class _Row:
    @property
    def cells(self) -> tuple[_Cell]: ...

class _Cell:
    @property
    def text(self) -> str: ...
