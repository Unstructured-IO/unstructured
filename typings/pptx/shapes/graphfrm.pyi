from pptx.shapes.base import BaseShape
from pptx.table import Table

class GraphicFrame(BaseShape):
    @property
    def table(self) -> Table: ...
