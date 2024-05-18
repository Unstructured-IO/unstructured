from pptx.parts.image import Image
from pptx.shapes.base import BaseShape

class _BasePicture(BaseShape): ...

class Picture(_BasePicture):
    @property
    def image(self) -> Image: ...
