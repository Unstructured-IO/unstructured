import logging
from dataclasses import dataclass, field
from typing import List
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
    text: str
    child_pages: List[str] = field(default_factory=List[str])
    child_databases: List[str] = field(default_factory=List[str])


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

    return TextExtractionResponse(
        text="\n".join([t for t in text if t]),
    )
