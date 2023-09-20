from typing import BinaryIO, Union

from pptx.shared import PartElementProxy
from pptx.slide import SlideLayouts, Slides

class Presentation(PartElementProxy):
    def save(self, file: Union[str, BinaryIO]) -> None: ...
    @property
    def slide_layouts(self) -> SlideLayouts: ...
    @property
    def slides(self) -> Slides: ...
