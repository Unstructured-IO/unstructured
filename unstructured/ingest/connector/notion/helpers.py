import enum
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from uuid import UUID

from htmlBuilder.attributes import Style, Type
from htmlBuilder.tags import (
    Body,
    Div,
    Head,
    Html,
    HtmlTag,
    Ol,
    Table,
    Td,
    Th,
    Title,
    Tr,
    Ul,
)
from notion_client.errors import APIResponseError

import unstructured.ingest.connector.notion.types.blocks as notion_blocks
from unstructured.ingest.connector.notion.client import Client
from unstructured.ingest.connector.notion.interfaces import BlockBase
from unstructured.ingest.connector.notion.types.block import Block
from unstructured.ingest.connector.notion.types.database import Database


@dataclass
class TextExtractionResponse:
    text: Optional[str] = None
    child_pages: List[str] = field(default_factory=list)
    child_databases: List[str] = field(default_factory=list)


@dataclass
class HtmlExtractionResponse:
    html: Optional[HtmlTag] = None
    child_pages: List[str] = field(default_factory=list)
    child_databases: List[str] = field(default_factory=list)


def extract_page_html(
    client: Client,
    page_id: str,
    logger: logging.Logger,
) -> HtmlExtractionResponse:
    page_id_uuid = UUID(page_id)
    html_elements: List[Tuple[BlockBase, HtmlTag]] = []
    parent_block: Block = client.blocks.retrieve(block_id=page_id)  # type: ignore
    head = None
    if isinstance(parent_block.block, notion_blocks.ChildPage):
        head = Head([], Title([], parent_block.block.title))
    child_pages: List[str] = []
    child_databases: List[str] = []
    parents: List[Tuple[int, Block]] = [(0, parent_block)]
    processed_block_ids = []
    while len(parents) > 0:
        level, parent = parents.pop(0)
        parent_html = parent.get_html()
        if parent_html:
            html_elements.append((parent.block, parent_html))
        logger.debug(f"processing block: {parent}")
        if isinstance(parent.block, notion_blocks.ChildPage) and parent.id != str(page_id_uuid):
            child_pages.append(parent.id)
            continue
        if isinstance(parent.block, notion_blocks.ChildDatabase):
            child_databases.append(parent.id)
            continue
        if isinstance(parent.block, notion_blocks.Table):
            table_response = build_table(client=client, table=parent)
            html_elements.append((parent.block, table_response.table_html))
            child_pages.extend(table_response.child_pages)
            child_databases.extend(table_response.child_databases)
            continue
        if isinstance(parent.block, notion_blocks.ColumnList):
            column_html = build_columned_list(client=client, column_parent=parent)
            html_elements.append((parent.block, column_html))
            continue
        if isinstance(parent.block, notion_blocks.BulletedListItem):
            bullet_list_resp = build_bulleted_list_children(
                client=client,
                bulleted_list_item_parent=parent,
            )
            if bullet_list_children := bullet_list_resp.child_list:
                html_elements.append((parent.block, bullet_list_children))
            continue
        if isinstance(parent.block, notion_blocks.NumberedListItem):
            numbered_list_resp = build_numbered_list_children(
                client=client,
                numbered_list_item_parent=parent,
            )
            if numbered_list_children := numbered_list_resp.child_list:
                html_elements.append((parent.block, numbered_list_children))
            continue
        if parent.block.can_have_children() and parent.has_children:
            children = []
            for children_block in client.blocks.children.iterate_list(  # type: ignore
                block_id=parent.id,
            ):
                children.extend(children_block)
            if children:
                logger.debug(f"Adding {len(children)} children from parent: {parent}")
                for child in children:
                    if child.id not in processed_block_ids:
                        parents.append((level + 1, child))
        processed_block_ids.append(parent)

    # Join list items
    joined_html_elements = []
    numbered_list_items = []
    bullet_list_items = []
    for block, html in html_elements:
        if isinstance(block, notion_blocks.BulletedListItem):
            bullet_list_items.append(html)
            continue
        if isinstance(block, notion_blocks.NumberedListItem):
            numbered_list_items.append(html)
            continue
        if len(numbered_list_items) > 0:
            joined_html_elements.append(Ol([], numbered_list_items))
            numbered_list_items = []
        if len(bullet_list_items) > 0:
            joined_html_elements.append(Ul([], bullet_list_items))
            bullet_list_items = []
        joined_html_elements.append(html)

    body = Body([], joined_html_elements)
    all_elements = [body]
    if head:
        all_elements = [head] + all_elements
    full_html = Html([], all_elements)
    return HtmlExtractionResponse(
        full_html,
        child_pages=child_pages,
        child_databases=child_databases,
    )


def extract_database_html(
    client: Client,
    database_id: str,
    logger: logging.Logger,
) -> HtmlExtractionResponse:
    logger.debug(f"processing database id: {database_id}")
    database: Database = client.databases.retrieve(database_id=database_id)  # type: ignore
    property_keys = list(database.properties.keys())
    property_keys = sorted(property_keys)
    table_html_rows = []
    child_pages: List[str] = []
    child_databases: List[str] = []
    # Create header row
    table_html_rows.append(Tr([], [Th([], k) for k in property_keys]))

    all_pages = []
    for page_chunk in client.databases.iterate_query(database_id=database_id):  # type: ignore
        all_pages.extend(page_chunk)

    logger.debug(f"Creating {len(all_pages)} rows")
    for page in all_pages:
        if is_database_url(client=client, url=page.url):
            child_databases.append(page.id)
        if is_page_url(client=client, url=page.url):
            child_pages.append(page.id)
        properties = page.properties
        inner_html = [properties.get(k).get_html() for k in property_keys]  # type: ignore
        table_html_rows.append(
            Tr(
                [],
                [Td([], cell) for cell in [html if html else Div([], []) for html in inner_html]],
            ),
        )

    table_html = Table([], table_html_rows)

    return HtmlExtractionResponse(
        html=table_html,
        child_pages=child_pages,
        child_databases=child_databases,
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
    child_pages: List[str] = []
    child_dbs: List[str] = []
    processed: List[str] = []
    while len(parents) > 0:
        parent: QueueEntry = parents.pop()
        processed.append(str(parent.id))
        if parent.type == QueueEntryType.PAGE:
            logger.debug(f"Getting child data from page: {parent.id}")
            page_children = []
            try:
                for children_block in client.blocks.children.iterate_list(  # type: ignore
                    block_id=str(parent.id),
                ):
                    page_children.extend(children_block)
            except APIResponseError as api_error:
                logger.error(f"failed to get page with id {parent.id}: {api_error}")
                if str(parent.id) in child_pages:
                    child_pages.remove(str(parent.id))
                continue
            if not page_children:
                continue

            # Extract child pages
            child_pages_from_page = [
                c for c in page_children if isinstance(c.block, notion_blocks.ChildPage)
            ]
            if child_pages_from_page:
                child_page_blocks: List[notion_blocks.ChildPage] = [
                    p.block
                    for p in child_pages_from_page
                    if isinstance(p.block, notion_blocks.ChildPage)
                ]
                logger.debug(
                    "found child pages from parent page {}: {}".format(
                        parent.id,
                        ", ".join([block.title for block in child_page_blocks]),
                    ),
                )
            new_pages = [p.id for p in child_pages_from_page if p.id not in processed]
            new_pages = list(set(new_pages))
            child_pages.extend(new_pages)
            parents.extend(
                [QueueEntry(type=QueueEntryType.PAGE, id=UUID(i)) for i in new_pages],
            )

            # Extract child databases
            child_dbs_from_page = [
                c for c in page_children if isinstance(c.block, notion_blocks.ChildDatabase)
            ]
            if child_dbs_from_page:
                child_db_blocks: List[notion_blocks.ChildDatabase] = [
                    c.block
                    for c in page_children
                    if isinstance(c.block, notion_blocks.ChildDatabase)
                ]
                logger.debug(
                    "found child database from parent page {}: {}".format(
                        parent.id,
                        ", ".join([block.title for block in child_db_blocks]),
                    ),
                )
            new_dbs = [db.id for db in child_dbs_from_page if db.id not in processed]
            new_dbs = list(set(new_dbs))
            child_dbs.extend(new_dbs)
            parents.extend(
                [QueueEntry(type=QueueEntryType.DATABASE, id=UUID(i)) for i in new_dbs],
            )

            linked_to_others: List[notion_blocks.LinkToPage] = [
                c.block for c in page_children if isinstance(c.block, notion_blocks.LinkToPage)
            ]
            for link in linked_to_others:
                if (page_id := link.page_id) and (
                    page_id not in processed and page_id not in child_pages
                ):
                    child_pages.append(page_id)
                    parents.append(QueueEntry(type=QueueEntryType.PAGE, id=UUID(page_id)))
                if (database_id := link.database_id) and (
                    database_id not in processed and database_id not in child_dbs
                ):
                    child_dbs.append(database_id)
                    parents.append(
                        QueueEntry(type=QueueEntryType.DATABASE, id=UUID(database_id)),
                    )

        elif parent.type == QueueEntryType.DATABASE:
            logger.debug(f"Getting child data from database: {parent.id}")
            database_pages = []
            try:
                for page_entries in client.databases.iterate_query(  # type: ignore
                    database_id=str(parent.id),
                ):
                    database_pages.extend(page_entries)
            except APIResponseError as api_error:
                logger.error(f"failed to get database with id {parent.id}: {api_error}")
                if str(parent.id) in child_dbs:
                    child_dbs.remove(str(parent.id))
                continue
            if not database_pages:
                continue

            child_pages_from_db = [
                p for p in database_pages if is_page_url(client=client, url=p.url)
            ]
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

            child_dbs_from_db = [
                p for p in database_pages if is_database_url(client=client, url=p.url)
            ]
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


def get_uuid_from_url(path: str) -> Optional[str]:
    strings = path.split("-")
    if len(strings) > 0 and is_valid_uuid(strings[-1]):
        return strings[-1]
    return None


def is_page_url(client: Client, url: str):
    parsed_url = urlparse(url)
    path = parsed_url.path.split("/")[-1]
    if parsed_url.netloc != "www.notion.so":
        return False
    page_uuid = get_uuid_from_url(path=path)
    if not page_uuid:
        return False
    check_resp = client.pages.retrieve_status(page_id=page_uuid)
    if check_resp == 200:
        return True
    return False


def is_database_url(client: Client, url: str):
    parsed_url = urlparse(url)
    path = parsed_url.path.split("/")[-1]
    if parsed_url.netloc != "www.notion.so":
        return False
    database_uuid = get_uuid_from_url(path=path)
    if not database_uuid:
        return False
    check_resp = client.databases.retrieve_status(database_id=database_uuid)
    if check_resp == 200:
        return True
    return False


@dataclass
class BuildTableResponse:
    table_html: HtmlTag
    child_pages: List[str] = field(default_factory=list)
    child_databases: List[str] = field(default_factory=list)


def build_table(client: Client, table: Block) -> BuildTableResponse:
    if not isinstance(table.block, notion_blocks.Table):
        raise ValueError(f"block type not table: {type(table.block)}")
    rows: List[notion_blocks.TableRow] = []
    child_pages: List[str] = []
    child_databases: List[str] = []
    for row_chunk in client.blocks.children.iterate_list(  # type: ignore
        block_id=table.id,
    ):
        rows.extend(
            [row.block for row in row_chunk if isinstance(row.block, notion_blocks.TableRow)],
        )

    # Extract child databases and pages
    for row in rows:
        for c in row.cells:
            for rt in c.rich_texts:
                if mention := rt.mention:
                    if mention.type == "page" and (page := mention.page):
                        child_pages.append(page.id)
                    if mention.type == "database" and (database := mention.database):
                        child_databases.append(database.id)

    header: Optional[notion_blocks.TableRow] = None
    if table.block.has_column_header:
        header = rows.pop(0)
    table_html_rows = []
    if header:
        header.is_header = True
        table_html_rows.append(header.get_html())
    table_html_rows.extend([row.get_html() for row in rows])
    html_table = Table([], table_html_rows)

    return BuildTableResponse(
        table_html=html_table,
        child_pages=child_pages,
        child_databases=child_databases,
    )


def build_columned_list(client: Client, column_parent: Block) -> HtmlTag:
    if not isinstance(column_parent.block, notion_blocks.ColumnList):
        raise ValueError(f"block type not column list: {type(column_parent.block)}")
    columns: List[Block] = []
    for column_chunk in client.blocks.children.iterate_list(  # type: ignore
        block_id=column_parent.id,
    ):
        columns.extend(column_chunk)
    num_columns = len(columns)
    columns_content = []
    for column in columns:
        for column_content_chunk in client.blocks.children.iterate_list(  # type: ignore
            block_id=column.id,
        ):
            columns_content.append(
                Div(
                    [Style(f"width:{100/num_columns}%; float: left")],
                    [content.block.get_html() for content in column_content_chunk],
                ),
            )

    return Div([], columns_content)


@dataclass
class BulletedListResponse:
    html: HtmlTag
    child_list: Optional[HtmlTag] = None


bulleted_list_styles = ["circle", "square", "disc"]


def build_bulleted_list_children(
    client: Client,
    bulleted_list_item_parent: Block,
    list_style_ind: int = 0,
) -> BulletedListResponse:
    if not isinstance(bulleted_list_item_parent.block, notion_blocks.BulletedListItem):
        raise ValueError(
            f"block type not bulleted list item: {type(bulleted_list_item_parent.block)}",
        )
    html = bulleted_list_item_parent.get_html()
    if html:
        html.attributes = [Style("margin-left: 10px")]
    if not bulleted_list_item_parent.has_children:
        return BulletedListResponse(
            html=html,
        )
    children = []
    for child_block in client.blocks.children.iterate_list(  # type: ignore
        block_id=bulleted_list_item_parent.id,
    ):
        children.extend(child_block)
    if not children:
        return BulletedListResponse(
            html=bulleted_list_item_parent.get_html(),
        )
    child_html = []
    for child in children:
        child_resp = build_bulleted_list_children(
            client=client,
            bulleted_list_item_parent=child,
            list_style_ind=(list_style_ind + 1) % len(bulleted_list_styles),
        )
        child_html.append(child_resp.html)
        if child_children := child_resp.child_list:
            child_html.append(child_children)

    return BulletedListResponse(
        html=html,
        child_list=Ul(
            [Style(f"list-style-type: {bulleted_list_styles[list_style_ind]}")],
            child_html,
        ),
    )


@dataclass
class NumberedListResponse:
    html: HtmlTag
    child_list: Optional[HtmlTag] = None


numbered_list_types = ["a", "i", "1"]


def build_numbered_list_children(
    client: Client,
    numbered_list_item_parent: Block,
    type_attr_ind=0,
) -> NumberedListResponse:
    if not isinstance(numbered_list_item_parent.block, notion_blocks.NumberedListItem):
        raise ValueError(
            f"block type not numbered list item: {type(numbered_list_item_parent.block)}",
        )
    html = numbered_list_item_parent.get_html()
    if html:
        html.attributes = [Style("margin-left: 10px")]
    if not numbered_list_item_parent.has_children:
        return NumberedListResponse(
            html=html,
        )
    children = []
    for child_block in client.blocks.children.iterate_list(  # type: ignore
        block_id=numbered_list_item_parent.id,
    ):
        children.extend(child_block)
    if not children:
        return NumberedListResponse(
            html=numbered_list_item_parent.get_html(),
        )
    child_html = []
    for child in children:
        child_resp = build_numbered_list_children(
            client=client,
            numbered_list_item_parent=child,
            type_attr_ind=(type_attr_ind + 1) % len(numbered_list_types),
        )
        child_html.append(child_resp.html)
        if child_children := child_resp.child_list:
            child_html.append(child_children)

    return NumberedListResponse(
        html=html,
        child_list=Ol([Type(numbered_list_types[type_attr_ind])], child_html),
    )
