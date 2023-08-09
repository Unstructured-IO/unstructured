# https://developers.notion.com/reference/block#image
from typing import Optional

from htmlBuilder.attributes import Src
from htmlBuilder.tags import HtmlTag, Source
from htmlBuilder.tags import Video as VideoHtml

from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.file import FileObject


class Video(BlockBase, FileObject):
    @staticmethod
    def can_have_children() -> bool:
        return False

    def get_html(self) -> Optional[HtmlTag]:
        if self.external:
            return VideoHtml([], [Source([Src(self.external.url)], [self.external.url])])
        if self.file:
            return VideoHtml([], [Source([Src(self.file.url)], [self.file.url])])
        return None
