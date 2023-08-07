import enum
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse
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
    child_pages: List[str] = []
    child_databases: List[str] = []
    database: Database = client.databases.retrieve(database_id=database_id)  # type: ignore
    text.append(database.get_text())
    for pages in client.databases.iterate_query(database_id=database_id):  # type: ignore
        for page in pages:
            if is_database_url(page.url):
                child_databases.append(page.id)
            if is_page_url(page.url):
                child_pages.append(page.id)
            for k, v in page.properties.items():
                text.append(v.get_text())

    non_empty_text = [t for t in text if t]
    return TextExtractionResponse(
        text="\n".join(non_empty_text) if non_empty_text else None,
        child_databases=child_databases,
        child_pages=child_pages,
    )


@dataclass
class ChildExtractionResponse:
    child_pages: List[str] = field(default_factory=list)
    child_databases: List[str] = field(default_factory=list)


class QueueEntryType(enum.Enum):
    DATABASE = "database"
    PAGE = "page"


@dataclass
class QueueEntry:
    type: QueueEntryType
    id: UUID


def get_recursive_content_from_page(
    client: Client,
    page_id: str,
    logger: logging.Logger,
) -> ChildExtractionResponse:
    return get_recursive_content(
        client=client,
        init_entry=QueueEntry(type=QueueEntryType.PAGE, id=UUID(page_id)),
        logger=logger,
    )


def get_recursive_content_from_database(
    client: Client,
    database_id: str,
    logger: logging.Logger,
) -> ChildExtractionResponse:
    return get_recursive_content(
        client=client,
        init_entry=QueueEntry(type=QueueEntryType.DATABASE, id=UUID(database_id)),
        logger=logger,
    )


def get_recursive_content(
    client: Client,
    init_entry: QueueEntry,
    logger: logging.Logger,
) -> ChildExtractionResponse:
    parents: List[QueueEntry] = [init_entry]
    child_pages = []
    child_dbs = []
    processed = []
    while len(parents) > 0:
        parent: QueueEntry = parents.pop()
        processed.append(parent.id)
        if parent.type == QueueEntryType.PAGE:
            logger.debug(f"Getting child data from page: {parent.id}")
            for children in client.blocks.children.iterate_list(  # type: ignore
                block_id=str(parent.id),
            ):
                child_pages_from_page = [c for c in children if isinstance(c.block, ChildPage)]
                if child_pages_from_page:
                    child_page_blocks: List[ChildPage] = [
                        p.block for p in child_pages_from_page if isinstance(p.block, ChildPage)
                    ]
                    logger.debug(
                        "found child pages from parent page {}: {}".format(
                            parent.id,
                            ", ".join([block.title for block in child_page_blocks]),
                        ),
                    )
                new_pages = [p.id for p in child_pages_from_page if p.id not in processed]
                child_pages.extend(new_pages)
                parents.extend(
                    [QueueEntry(type=QueueEntryType.PAGE, id=UUID(i)) for i in new_pages],
                )

                child_dbs_from_page = [c for c in children if isinstance(c.block, ChildDatabase)]
                if child_dbs_from_page:
                    child_db_blocks: List[ChildDatabase] = [
                        c.block for c in children if isinstance(c.block, ChildDatabase)
                    ]
                    logger.debug(
                        "found child database from parent page {}: {}".format(
                            parent.id,
                            ", ".join([block.title for block in child_db_blocks]),
                        ),
                    )
                new_dbs = [db.id for db in child_dbs_from_page if db.id not in processed]
                child_dbs.extend(new_dbs)
                parents.extend(
                    [QueueEntry(type=QueueEntryType.DATABASE, id=UUID(i)) for i in new_dbs],
                )
        elif parent.type == QueueEntryType.DATABASE:
            logger.debug(f"Getting child data from database: {parent.id}")
            for page_entries in client.databases.iterate_query(  # type: ignore
                database_id=str(parent.id),
            ):
                child_pages_from_db = [p for p in page_entries if is_page_url(p.url)]
                if child_pages_from_db:
                    logger.debug(
                        "found child pages from parent database {}: {}".format(
                            parent.id,
                            ", ".join([p.url for p in child_pages_from_db]),
                        ),
                    )
                new_pages = [p.id for p in child_pages_from_db if p.id not in processed]
                child_pages.extend(new_pages)
                parents.extend(
                    [QueueEntry(type=QueueEntryType.PAGE, id=UUID(i)) for i in new_pages],
                )

                child_dbs_from_db = [p for p in page_entries if is_database_url(p.url)]
                if child_dbs_from_db:
                    logger.debug(
                        "found child database from parent database {}: {}".format(
                            parent.id,
                            ", ".join([db.url for db in child_dbs_from_db]),
                        ),
                    )
                new_dbs = [db.id for db in child_dbs_from_db if db.id not in processed]
                child_dbs.extend(new_dbs)
                parents.extend(
                    [QueueEntry(type=QueueEntryType.DATABASE, id=UUID(i)) for i in new_dbs],
                )

    return ChildExtractionResponse(
        child_pages=child_pages,
        child_databases=child_dbs,
    )


def is_valid_uuid(uuid_str: str) -> bool:
    try:
        UUID(uuid_str)
        return True
    except Exception:
        return False


def is_page_url(url: str):
    parsed_url = urlparse(url)
    path = parsed_url.path.split("/")[-1]
    if parsed_url.netloc != "www.notion.so":
        return False
    if is_valid_uuid(path):
        return False
    strings = path.split("-")
    if len(strings) > 0 and is_valid_uuid(strings[-1]):
        return True
    return False


def is_database_url(url: str):
    parsed_url = urlparse(url)
    path = parsed_url.path.split("/")[-1]
    if parsed_url.netloc != "www.notion.so":
        return False
    return is_valid_uuid(path)
