from typing import IO, Union

from pptx.shared import PartElementProxy
from pptx.slide import SlideLayouts, Slides

class Presentation(PartElementProxy):
    def save(self, file: Union[str, IO[bytes]]) -> None: ...
    @property
    def slide_layouts(self) -> SlideLayouts: ...
    @property
    def slides(self) -> Slides: ...
