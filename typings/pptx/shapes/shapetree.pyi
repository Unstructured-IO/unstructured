from typing import Iterator

from pptx.shapes.autoshape import Shape
from pptx.shapes.base import BaseShape
from pptx.shared import ParentedElementProxy
from pptx.util import Length

class _BaseShapes(ParentedElementProxy):
    def __iter__(self) -> Iterator[BaseShape]: ...

class _BaseGroupShapes(_BaseShapes):
    def add_textbox(self, left: Length, top: Length, width: Length, height: Length) -> Shape: ...

class GroupShapes(_BaseGroupShapes): ...
class NotesSlideShapes(_BaseShapes): ...

class SlideShapes(_BaseGroupShapes):
    def __iter__(self) -> Iterator[BaseShape]: ...
    @property
    def title(self) -> Shape | None: ...
