from pptx.shared import PartElementProxy
from pptx.slide import Slides

class Presentation(PartElementProxy):
    @property
    def slides(self) -> Slides: ...
