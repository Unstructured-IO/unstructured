from pptx.shapes.base import BaseShape
from pptx.shapes.shapetree import GroupShapes

class GroupShape(BaseShape):
    @property
    def shapes(self) -> GroupShapes: ...
