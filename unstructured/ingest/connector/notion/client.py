from typing import Any, Generator, List, Tuple

from notion_client import Client as NotionClient
from notion_client.api_endpoints import (
    BlocksChildrenEndpoint as NotionBlocksChildrenEndpoint,
)
from notion_client.api_endpoints import BlocksEndpoint as NotionBlocksEndpoint
from notion_client.api_endpoints import PagesEndpoint as NotionPagesEndpoint

from unstructured.ingest.connector.notion.types.block import Block
from unstructured.ingest.connector.notion.types.page import Page


class BlocksChildrenEndpoint(NotionBlocksChildrenEndpoint):
    def list(self, block_id: str, **kwargs: Any) -> Tuple[List[Block], dict]:
        resp: dict = super().list(block_id=block_id, **kwargs)  # type: ignore
        child_blocks = [Block.from_dict(data=b) for b in resp.pop("results", [])]
        return child_blocks, resp

    def iterate_list(
        self,
        block_id: str,
        **kwargs: Any,
    ) -> Generator[List[Block], None, None]:
        while True:
            response: dict = super().list(block_id=block_id, **kwargs)  # type: ignore
            child_blocks = [Block.from_dict(data=b) for b in response.pop("results", [])]
            yield child_blocks

            next_cursor = response.get("next_cursor")
            if not response.get("has_more") or not next_cursor:
                return


class BlocksEndpoint(NotionBlocksEndpoint):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.children = BlocksChildrenEndpoint(*args, **kwargs)

    def retrieve(self, block_id: str, **kwargs: Any) -> Block:
        resp: dict = super().retrieve(block_id=block_id, **kwargs)  # type: ignore
        return Block.from_dict(data=resp)


class PagesEndpoint(NotionPagesEndpoint):
    def retrieve(self, page_id: str, **kwargs: Any) -> Page:
        resp: dict = super().retrieve(page_id=page_id, **kwargs)  # type: ignore
        return Page.from_dict(data=resp)


class Client(NotionClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.blocks = BlocksEndpoint(self)
        self.pages = PagesEndpoint(self)
