# https://developers.notion.com/reference/block#image
from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.file import FileObject


class Image(BlockBase, FileObject):
    @staticmethod
    def can_have_children() -> bool:
        return False
