import logging
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from unstructured.ingest.connector.notion.client import Client
from unstructured.ingest.connector.notion.types.block import Block
from unstructured.ingest.connector.notion.types.blocks.child_database import (
    ChildDatabase,
)
from unstructured.ingest.connector.notion.types.blocks.child_page import ChildPage
from unstructured.ingest.connector.notion.types.database import Database


@dataclass
class TextExtractionResponse:
    text: Optional[str] = None
    child_pages: List[str] = field(default_factory=list)
    child_databases: List[str] = field(default_factory=list)


def extract_page_text(
    client: Client,
    page_id: str,
    logger: logging.Logger,
) -> TextExtractionResponse:
    page_id_uuid = UUID(page_id)
    text: List[str] = []
    parent_block: Block = client.blocks.retrieve(block_id=page_id)  # type: ignore

    child_pages: List[str] = []
    child_databases: List[str] = []
    parents: List[Block] = [parent_block]
    processed_block_ids = []
    while len(parents) > 0:
        parent = parents.pop(0)
        parent_text = parent.get_text()
        if parent_text:
            text.append(parent_text)
        logger.debug(f"processing block: {parent}")
        if isinstance(parent.block, ChildPage) and parent.id != str(page_id_uuid):
            child_pages.append(parent.id)
            continue
        if isinstance(parent.block, ChildDatabase):
            child_databases.append(parent.id)
            continue
        if parent.block.can_have_children() and parent.has_children:
            for children in client.blocks.children.iterate_list(block_id=parent.id):  # type: ignore
                for child in children:
                    if child.id not in processed_block_ids:
                        parents.append(child)
        processed_block_ids.append(parent)
    return TextExtractionResponse(
        text="\n".join(text),
        child_pages=child_pages,
        child_databases=child_databases,
    )


def extract_database_text(
    client: Client,
    database_id: str,
    logger: logging.Logger,
) -> TextExtractionResponse:
    logger.debug(f"processing database id: {database_id}")
    UUID(database_id)
    text = []
    database: Database = client.databases.retrieve(database_id=database_id)  # type: ignore
    text.append(database.get_text())
    for database_rows in client.databases.iterate_query(database_id=database_id):  # type: ignore
        for database_row in database_rows:
            for k, v in database_row.properties.items():
                text.append(v.get_text())

    non_empty_text = [t for t in text if t]
    return TextExtractionResponse(
        text="\n".join(non_empty_text) if non_empty_text else None,
    )


@dataclass
class ChildExtractionResponse:
    child_pages: List[str] = field(default_factory=list)
    child_databases: List[str] = field(default_factory=list)


def get_recursive_content(client: Client, page_id: str) -> ChildExtractionResponse:
    parent_ids = [page_id]
    child_pages = []
    child_dbs = []
    processed = []
    while len(parent_ids) > 0:
        parent_id = parent_ids.pop()
        for children in client.blocks.children.iterate_list(block_id=parent_id):  # type: ignore
            processed.append(parent_id)

            pages = [c.id for c in children if isinstance(c.block, ChildPage)]
            new_pages = [p for p in pages if p not in processed]
            child_pages.extend(new_pages)
            parent_ids.extend(new_pages)

            dbs = [c.id for c in children if isinstance(c.block, ChildDatabase)]
            new_dbs = [db for db in dbs if db not in processed]
            child_dbs.extend(new_dbs)
            parent_ids.extend(new_dbs)

    return ChildExtractionResponse(
        child_pages=child_pages,
        child_databases=child_dbs,
    )
