from pptx.shapes.base import BaseShape
from pptx.text.text import TextFrame

class Shape(BaseShape):
    text: str
    @property
    def text_frame(self) -> TextFrame: ...
