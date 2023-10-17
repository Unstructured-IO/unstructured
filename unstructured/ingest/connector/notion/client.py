from typing import Any, Generator, List, Optional, Tuple

import backoff
import httpx
import notion_client.errors
from notion_client import Client as NotionClient
from notion_client.api_endpoints import BlocksChildrenEndpoint as NotionBlocksChildrenEndpoint
from notion_client.api_endpoints import BlocksEndpoint as NotionBlocksEndpoint
from notion_client.api_endpoints import DatabasesEndpoint as NotionDatabasesEndpoint
from notion_client.api_endpoints import Endpoint
from notion_client.api_endpoints import PagesEndpoint as NotionPagesEndpoint
from notion_client.errors import RequestTimeoutError

from unstructured.ingest.connector.notion.types.block import Block
from unstructured.ingest.connector.notion.types.database import Database
from unstructured.ingest.connector.notion.types.database_properties import (
    map_cells,
)
from unstructured.ingest.connector.notion.types.page import Page
from unstructured.ingest.ingest_backoff import RetryHandler
from unstructured.ingest.interfaces import RetryStrategyConfig

retryable_exceptions = (
    httpx.TimeoutException,
    httpx.HTTPStatusError,
    notion_client.errors.HTTPResponseError,
)


def get_retry_handler(endpoint: Endpoint) -> Optional[RetryHandler]:
    if retry_strategy_config := getattr(endpoint, "retry_strategy_config"):
        return RetryHandler(
            backoff.expo,
            retryable_exceptions,
            max_time=retry_strategy_config.max_retry_time,
            max_tries=retry_strategy_config.max_retries,
            logger=endpoint.parent.logger,
            start_log_level=endpoint.parent.logger.level,
            backoff_log_level=endpoint.parent.logger.level,
        )
    return None


class BlocksChildrenEndpoint(NotionBlocksChildrenEndpoint):
    def __init__(
        self,
        *args,
        retry_strategy_config: Optional[RetryStrategyConfig] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.retry_strategy_config = retry_strategy_config

    @property
    def retry_handler(self) -> Optional[RetryHandler]:
        return get_retry_handler(self)

    def list(self, block_id: str, **kwargs: Any) -> Tuple[List[Block], dict]:
        resp: dict = (
            self.retry_handler(super().list, block_id=block_id, **kwargs)
            if self.retry_handler
            else super().list(block_id=block_id, **kwargs)
        )  # type: ignore
        child_blocks = [Block.from_dict(data=b) for b in resp.pop("results", [])]
        return child_blocks, resp

    def iterate_list(
        self,
        block_id: str,
        **kwargs: Any,
    ) -> Generator[List[Block], None, None]:
        while True:
            response: dict = (
                self.retry_handler(super().list, block_id=block_id, **kwargs)
                if self.retry_handler
                else super().list(block_id=block_id, **kwargs)
            )  # type: ignore
            child_blocks = [Block.from_dict(data=b) for b in response.pop("results", [])]
            yield child_blocks

            next_cursor = response.get("next_cursor")
            if not response.get("has_more") or not next_cursor:
                return


class DatabasesEndpoint(NotionDatabasesEndpoint):
    def __init__(
        self,
        *args,
        retry_strategy_config: Optional[RetryStrategyConfig] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.retry_strategy_config = retry_strategy_config

    @property
    def retry_handler(self) -> Optional[RetryHandler]:
        return get_retry_handler(self)

    def retrieve(self, database_id: str, **kwargs: Any) -> Database:
        resp: dict = (
            self.retry_handler(super().retrieve, database_id=database_id, **kwargs)
            if (self.retry_handler)
            else (super().retrieve(database_id=database_id, **kwargs))
        )  # type: ignore
        return Database.from_dict(data=resp)

    def retrieve_status(self, database_id: str, **kwargs) -> int:
        request = self.parent._build_request(
            method="HEAD",
            path=f"databases/{database_id}",
            auth=kwargs.get("auth"),
        )
        try:
            response: httpx.Response = (
                self.retry_handler(self.parent.client.send, request)
                if (self.retry_handler)
                else (self.parent.client.send(request))
            )  # type: ignore
            return response.status_code
        except httpx.TimeoutException:
            raise RequestTimeoutError()

    def query(self, database_id: str, **kwargs: Any) -> Tuple[List[Page], dict]:
        """Get a list of [Pages](https://developers.notion.com/reference/page) contained in the database.

        *[🔗 Endpoint documentation](https://developers.notion.com/reference/post-database-query)*
        """  # noqa: E501
        resp: dict = (
            self.retry_handler(super().query, database_id=database_id, **kwargs)
            if (self.retry_handler)
            else (super().query(database_id=database_id, **kwargs))
        )  # type: ignore
        pages = [Page.from_dict(data=p) for p in resp.pop("results")]
        for p in pages:
            p.properties = map_cells(p.properties)
        return pages, resp

    def iterate_query(self, database_id: str, **kwargs: Any) -> Generator[List[Page], None, None]:
        while True:
            response: dict = (
                self.retry_handler(super().query, database_id=database_id, **kwargs)
                if (self.retry_handler)
                else (super().query(database_id=database_id, **kwargs))
            )  # type: ignore
            pages = [Page.from_dict(data=p) for p in response.pop("results", [])]
            for p in pages:
                p.properties = map_cells(p.properties)
            yield pages

            next_cursor = response.get("next_cursor")
            if not response.get("has_more") or not next_cursor:
                return


class BlocksEndpoint(NotionBlocksEndpoint):
    def __init__(
        self,
        *args: Any,
        retry_strategy_config: Optional[RetryStrategyConfig] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.retry_strategy_config = retry_strategy_config
        self.children = BlocksChildrenEndpoint(
            retry_strategy_config=retry_strategy_config,
            *args,
            **kwargs,
        )

    @property
    def retry_handler(self) -> Optional[RetryHandler]:
        return get_retry_handler(self)

    def retrieve(self, block_id: str, **kwargs: Any) -> Block:
        resp: dict = (
            self.retry_handler(super().retrieve, block_id=block_id, **kwargs)
            if (self.retry_handler)
            else (super().retrieve(block_id=block_id, **kwargs))
        )  # type: ignore
        return Block.from_dict(data=resp)


class PagesEndpoint(NotionPagesEndpoint):
    def __init__(
        self,
        *args,
        retry_strategy_config: Optional[RetryStrategyConfig] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.retry_strategy_config = retry_strategy_config

    @property
    def retry_handler(self) -> Optional[RetryHandler]:
        return get_retry_handler(self)

    def retrieve(self, page_id: str, **kwargs: Any) -> Page:
        resp: dict = (
            self.retry_handler(super().retrieve, page_id=page_id, **kwargs)
            if (self.retry_handler)
            else (super().retrieve(page_id=page_id, **kwargs))
        )  # type: ignore
        return Page.from_dict(data=resp)

    def retrieve_status(self, page_id: str, **kwargs) -> int:
        request = self.parent._build_request(
            method="HEAD",
            path=f"pages/{page_id}",
            auth=kwargs.get("auth"),
        )
        try:
            response: httpx.Response = (
                self.retry_handler(self.parent.client.send, request)
                if (self.retry_handler)
                else (self.parent.client.send(request))
            )  # type: ignore
            return response.status_code
        except httpx.TimeoutException:
            raise RequestTimeoutError()


class Client(NotionClient):
    def __init__(
        self,
        *args: Any,
        retry_strategy_config: Optional[RetryStrategyConfig] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.blocks = BlocksEndpoint(retry_strategy_config=retry_strategy_config, parent=self)
        self.pages = PagesEndpoint(retry_strategy_config=retry_strategy_config, parent=self)
        self.databases = DatabasesEndpoint(retry_strategy_config=retry_strategy_config, parent=self)
