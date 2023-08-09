from typing import Any, Generator, List, Tuple

from notion_client import Client as NotionClient
from notion_client.api_endpoints import (
    BlocksChildrenEndpoint as NotionBlocksChildrenEndpoint,
)
from notion_client.api_endpoints import BlocksEndpoint as NotionBlocksEndpoint
from notion_client.api_endpoints import DatabasesEndpoint as NotionDatabasesEndpoint
from notion_client.api_endpoints import PagesEndpoint as NotionPagesEndpoint

from unstructured.ingest.connector.notion.types.block import Block
from unstructured.ingest.connector.notion.types.database import Database
from unstructured.ingest.connector.notion.types.database_properties import (
    map_cells,
)
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


class DatabasesEndpoint(NotionDatabasesEndpoint):
    def retrieve(self, database_id: str, **kwargs: Any) -> Database:
        resp: dict = super().retrieve(database_id=database_id, **kwargs)  # type: ignore
        return Database.from_dict(data=resp)

    def query(self, database_id: str, **kwargs: Any) -> Tuple[List[Page], dict]:
        """Get a list of [Pages](https://developers.notion.com/reference/page) contained in the database.

        *[🔗 Endpoint documentation](https://developers.notion.com/reference/post-database-query)*
        """  # noqa: E501
        resp: dict = super().query(database_id=database_id, **kwargs)  # type: ignore
        pages = [Page.from_dict(data=p) for p in resp.pop("results")]
        for p in pages:
            p.properties = map_cells(p.properties)
        return pages, resp

    def iterate_query(self, database_id: str, **kwargs: Any) -> Generator[List[Page], None, None]:
        while True:
            response: dict = super().query(database_id=database_id, **kwargs)  # type: ignore
            pages = [Page.from_dict(data=p) for p in response.pop("results", [])]
            for p in pages:
                p.properties = map_cells(p.properties)
            yield pages

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
        self.databases = DatabasesEndpoint(self)
