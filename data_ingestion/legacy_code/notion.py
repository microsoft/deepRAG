from dataclasses import dataclass
from datetime import datetime

import structlog

from typing import Any, Optional, Tuple

from langchain_core.documents import Document
from notion_client import AsyncClient, APIResponseError

from customer_care_agent.model.notion_page import NotionPage
from customer_care_agent.model.product_agent_info import RagSource
from customer_care_agent.settings import settings
from customer_care_agent.utils.bs_html_loader import CustomBSHTMLLoader

logger = structlog.get_logger("notion")

# Initialize Notion client
notion = AsyncClient(auth=settings.notion_secret)

# Notion API objects keys
ID_KEY = "id"
PAGE_ID_KEY = "page_id"
DATABASE_ID_KEY = "database_id"

PARENT_KEY = "parent"
PAGE_KEY = "page"
DATABASE_KEY = "database"

CHILD_PAGE_KEY = "child_page"
CHILD_DATABASE_KEY = "child_database"
LAST_EDIT_TIME_KEY = "last_edited_time"

RESULTS_KEY = "results"
NEXT_CURSOR_KEY = "next_cursor"

PROPERTIES_KEY = "properties"
TITLE_KEY = "title"
TYPE_KEY = "type"
OBJECT_KEY = "object"
PLAIN_TEXT_KEY = "plain_text"
RICH_TEXT_KEY = "rich_text"
ICON_KEY = "icon"
EMOJI_KEY = "emoji"
NAME_KEY = "name"
URL_KEY = "url"
HREF_KEY = "href"
TEXT_KEY = "text"
EXTERNAL_KEY = "external"
FILE_KEY = "file"
EXPRESSION_KEY = "expression"
CHECKED_KEY = "checked"
TABLE_WIDTH_KEY = "table_width"
HAS_COLUMN_HEADER_KEY = "has_column_header"
HAS_ROW_HEADER_KEY = "has_row_header"
CELLS_KEY = "cells"
HAS_CHILDREN_KEY = "has_children"
ANNOTATIONS_KEY = "annotations"
CODE_KEY = "code"
BOLD_KEY = "bold"
ITALIC_KEY = "italic"
STRIKETHROUGH_KEY = "strikethrough"
UNDERLINE_KEY = "underline"
NUMBER_KEY = "number"
START_DATE_KEY = "start"


@dataclass
class ChildPageOrDatabase:
    type: str
    id: str


# Fetches a page and its child pages as documents
async def get_notion_page_tree_as_documents(root_page_id: str) -> list[Document]:
    """
    Fetches a page and its child pages as documents
    :param root_page_id: Notion page id
    :return: List of documents
    """

    logger.info("Fetching a page and its child pages", page_id=root_page_id)

    # Fetch the page and its child pages
    notion_pages = await get_notion_pages(root_page_id)

    logger.info(
        "Fetched a page and its child pages",
        page_id=root_page_id,
        size=len(notion_pages),
    )

    # Convert the page and its child pages to documents
    notion_pages_as_documents = [
        CustomBSHTMLLoader(
            id=notion_page.id,
            content=notion_page.html,
            title=notion_page.title,
            source=notion_page.url,
            timestamp=datetime.now().isoformat(),
            integration=str(RagSource.NOTION),
            visibility="INTERNAL",
            use_break_line=False,
        ).load()
        for notion_page in notion_pages
    ]

    # Flatten the list of documents
    documents = [doc for sublist in notion_pages_as_documents for doc in sublist]

    logger.info(
        "Converted a page and its child pages to documents",
        page_id=root_page_id,
        size=len(documents),
    )

    return documents


# Fetches a single page as documents
async def get_notion_page_as_documents(page_id: str) -> list[Document]:
    """
    Fetches a single page as documents

    :param page_id: Notion page id
    :return: List of documents
    """

    logger.info("Fetching a single page", page_id=page_id)

    # Fetch the page
    notion_page, found_pages_databases = await get_notion_page(page_id)

    if notion_page:
        # Convert the page to documents
        documents = CustomBSHTMLLoader(
            content=notion_page.html,
            title=notion_page.title,
            source=notion_page.url,
            timestamp=notion_page.last_edited_time,
            integration="notion",
            use_break_line=False,
        ).load()

        return documents

    return []


# Fetches a page and its child pages
async def get_notion_pages(
    page_id: str, notion_pages: Optional[list[NotionPage]] = None
) -> list[NotionPage]:
    """
    Fetches a page and its child pages
    :param page_id: Notion page id
    :param notion_pages: List of Notion pages
    :return: List of Notion pages
    """

    # Fetches a page and its child pages
    if notion_pages is None:
        notion_pages = []

    # Fetch the page and its child pages and databases
    notion_page, child_pages_databases = await get_notion_page(page_id)

    if notion_page:
        # Append the fetched page to the list of pages
        notion_pages.append(notion_page)

        # Filter the child pages
        child_pages = [page for page in child_pages_databases if page.type == PAGE_KEY]

        # Filter the child databases
        child_databases = [
            database
            for database in child_pages_databases
            if database.type == DATABASE_KEY
        ]

        # Fetch the child database(s) page(s)
        for database in child_databases:
            database_pages = await get_database_pages(database.id)
            # Append the fetched database page(s) to the list of child pages
            child_pages.extend(database_pages)

        # Fetch the child page(s)
        for page in child_pages:
            await get_notion_pages(page.id, notion_pages)

    return notion_pages


# Fetches a page by its id from Notion
async def find_page(page_id: str) -> Any:
    """
    Fetches a page by its id from Notion
    :param page_id: Notion page id
    :return: Notion page
    """
    logger.info("Fetching a page", page_id=page_id)
    return await notion.pages.retrieve(page_id=page_id)


# Fetches a database by its id from Notion
async def find_database(database_id: str) -> Any:
    """
    Fetches a database by its id from Notion
    :param database_id: Notion database id
    :return: Notion database
    """
    logger.info("Fetching a database", database_id=database_id)
    return await notion.databases.retrieve(database_id=database_id)


# Fetches the database child pages
async def get_database_pages(database_id: str) -> list[ChildPageOrDatabase]:
    """
    Converts a database id into a list of database pages
    :param database_id: Notion database id
    :return: List of database pages
    """
    logger.info("Converting a database to HTML", database_id=database_id)

    try:
        # Fetch the database content
        database_entries = await get_database_entries(database_id)

        # Initialize the list of database pages
        database_pages: list[ChildPageOrDatabase] = []

        # Filter the database entries
        for database_entry in database_entries:
            if database_entry[OBJECT_KEY] == PAGE_KEY:
                # Append the fetched database page to the list of database pages
                database_pages.append(
                    ChildPageOrDatabase(id=database_entry[ID_KEY], type=PAGE_KEY)
                )

        return database_pages

    except APIResponseError as e:
        logger.warn(
            "Failed to convert database to HTML", database_id=database_id, error=e
        )
        return []


# Gets a notion page already converted to HTML and its child pages
async def get_notion_page(
    page_id: str,
) -> Tuple[NotionPage | None, list[ChildPageOrDatabase]]:
    """
    Gets a notion page already converted to HTML and its child pages
    :param page_id: Notion page id
    :return: Notion page and its child pages
    """

    logger.info("Getting a notion page", page_id=page_id)

    # Fetch the page
    page = await find_page(page_id)

    if "in_trash" in page and page["in_trash"]:
        return None, []

    # Fetch the blocks of the page
    blocks = await get_page_blocks(page_id)

    # Initialize the list of found HTML blocks and child pages databases
    found_html_blocks = []
    found_pages_databases = []

    # Convert the blocks of the page to HTML and finds the child pages and databases
    for block in blocks:
        html_slice, child_pages_databases = await convert_page_block_to_html(
            block=block
        )
        found_html_blocks.append(html_slice)
        found_pages_databases.extend(child_pages_databases)

    # Joins all blocks of the page into a single HTML block
    html_content = "".join([html_slice for html_slice in found_html_blocks])

    page_title = get_page_name(page)

    # Initialize the properties HTML
    properties_html = None

    # If the page is a database, convert the database properties to HTML
    if page[PARENT_KEY][TYPE_KEY] == DATABASE_ID_KEY:
        property_names = page[PROPERTIES_KEY].keys()
        properties_html = "".join(
            [
                convert_database_block_to_html(prop, page[PROPERTIES_KEY][prop])
                for prop in property_names
            ]
        )

    # Combines the page title, properties, and content into a single HTML page
    # If the page is a database page, the properties are included in the HTML
    # Otherwise the properties are not included
    page_html = (
        f"<h1>{page_title}</h1>{properties_html}<hr>{html_content}"
        if properties_html
        else f"<h1>{page_title}</h1>{html_content}"
    )

    # Returns the page and its child pages and databases
    return NotionPage(
        id=page_id,
        title=page_title,
        last_edited_time=page[LAST_EDIT_TIME_KEY],
        url=page[URL_KEY],
        html=page_html,
    ), found_pages_databases


def get_page_name(page: dict[str, Any]) -> str:
    """
    Finds the title of a page
    :param page: Notion page
    :return: Page title
    """
    # Finds the title of the page
    # If the page is a database, the title is found in the properties, in the property with the title type
    if page[PARENT_KEY][TYPE_KEY] == DATABASE_ID_KEY:
        title_property = next(
            (
                property_key
                for property_key in page[PROPERTIES_KEY].keys()
                if page[PROPERTIES_KEY][property_key][TYPE_KEY] == TITLE_KEY
            ),
            None,
        )

        page_title = "".join(
            [
                text[PLAIN_TEXT_KEY]
                for text in page[PROPERTIES_KEY][title_property][TITLE_KEY]
            ]
        )
    # If the page is not a database, the title is found in the default title property
    else:
        page_title = "".join(
            [
                text[PLAIN_TEXT_KEY]
                for text in page[PROPERTIES_KEY][TITLE_KEY][TITLE_KEY]
            ]
        )

    return page_title


# Recursively fetches all the content of a page
async def get_page_blocks(
    page_id: str, cursor: Optional[str] = None, blocks: Optional[list[Any]] = None
) -> list[dict[str, Any]]:
    """
    Recursively fetches all the content blocks of a page
    :param page_id: Notion page id
    :param cursor: Pagination cursor
    :param blocks: List of blocks
    :return: List of blocks
    """

    logger.debug("Fetching page blocks", page_id=page_id)

    # Initialize the blocks list
    if blocks is None:
        blocks = []

    try:
        # Fetch the page content
        response = await notion.blocks.children.list(
            block_id=page_id, start_cursor=cursor, page_size=500
        )

        # Append the fetched blocks to the blocks list
        blocks.extend(response.get(RESULTS_KEY, []))

        # Saves the next cursor to get the next page of results
        next_cursor = response.get(NEXT_CURSOR_KEY)

        # If there is a next cursor, fetch the next page of results
        if next_cursor:
            return await get_page_blocks(page_id, cursor=next_cursor, blocks=blocks)
    except APIResponseError as e:
        logger.error("Failed to fetch page blocks", page_id=page_id, error=e)
        return []

    return blocks


# Recursively fetches all the content of a database
async def get_database_entries(
    database_id: str,
    cursor: Optional[str] = None,
    database_entries: Optional[list[Any]] = None,
) -> list[dict[str, Any]]:
    """
    Recursively fetches all the content entries of a database
    :param database_id: Notion database id
    :param cursor: Pagination cursor
    :param database_entries: List of database entries
    :return: List of database entries
    """

    logger.debug("Fetching database entries", database_id=database_id)

    # Initialize the database entries list
    if database_entries is None:
        database_entries = []

    # Fetch the database content
    response = await notion.databases.query(
        database_id=database_id,
        filter={"or": []},
        sorts=[],
        start_cursor=cursor,
        page_size=500,
    )

    # Append the fetched entries to the database entries list
    database_entries.extend(response.get(RESULTS_KEY, []))

    # Saves the next cursor to get the next page of results
    next_cursor = response.get(NEXT_CURSOR_KEY)

    # If there is a next cursor, fetch the next page of results
    if next_cursor:
        return await get_database_entries(
            database_id, cursor=next_cursor, database_entries=database_entries
        )

    return database_entries


# Transforms a page block into HTML
async def convert_page_block_to_html(
    block: dict[str, Any],
    found_pages_databases: Optional[list[ChildPageOrDatabase]] = None,
    should_break_line: Optional[bool] = True,
) -> Tuple[str, list[ChildPageOrDatabase]]:
    """
    Transforms a page block into HTML
    :param block: Notion page block
    :param found_pages_databases: List of found pages and databases
    :param should_break_line: Whether to add a break line after the block
    :return: HTML block and list of found pages and databases
    """

    logger.debug("Converting a page block to HTML")

    if found_pages_databases is None:
        found_pages_databases = []

    # Get the content of the block
    content = block[block[TYPE_KEY]]

    # Block type heading_1 to HTML
    async def heading_1(child_block: Optional[str] = None) -> str:
        return await simple_html_tag("h2", child_block)

    # Block type heading_2 to HTML
    async def heading_2(child_block: Optional[str] = None) -> str:
        return await simple_html_tag("h3", child_block)

    # Block type heading_3 to HTML
    async def heading_3(child_block: Optional[str] = None) -> str:
        return await simple_html_tag("h4", child_block)

    # Block type quote to HTML
    async def quote(child_block: Optional[str] = None) -> str:
        return await simple_html_tag("blockquote", child_block)

    # Block type template to HTML
    async def template(child_block: Optional[str] = None) -> str:
        return await simple_html_tag("div", child_block)

    # Block type numbered_list_item to HTML
    async def numbered_list_item(child_block: Optional[str] = None) -> str:
        return await bulleted_list_item(child_block)

    # Block type divider to HTML
    async def divider(child_block: Optional[str] = None) -> str:
        return "<hr>"

    # Block type bookmark to HTML
    async def bookmark(child_block: Optional[str] = None) -> str:
        return f"<p>Bookmark: {content[URL_KEY]}</p>"

    # Block type embed to HTML
    async def embed(child_block: Optional[str] = None) -> str:
        return f"<iframe src='{content[URL_KEY]}'></iframe>"

    # Block type equation to HTML
    async def equation(child_block: Optional[str] = None) -> str:
        return f"<div>{content[EXPRESSION_KEY]}</div>"

    # Block type link_to_page to HTML
    async def link_to_page(child_block: Optional[str] = None) -> str:
        title = None
        url = None

        if content[TYPE_KEY] == PAGE_ID_KEY:
            page = await find_page(content[PAGE_ID_KEY])
            title = get_page_name(page)
            url = page[URL_KEY]
        elif content[TYPE_KEY] == DATABASE_ID_KEY:
            database = await find_database(content[DATABASE_ID_KEY])
            title = database[URL_KEY]
            url = database[URL_KEY]

        if title and url:
            return f"<p>{title}: {url}</p>"

        return ""

    # Block type link_to_page to HTML
    async def mention(child_block: Optional[str] = None) -> str:
        return f"{block[PLAIN_TEXT_KEY]} ({block[HREF_KEY]})"

    # Block type link_preview to HTML
    async def link_preview(child_block: Optional[str] = None) -> str:
        return f"<p>Preview: {content[URL_KEY]}</p>"

    # Block type simple_html_tag to HTML
    async def simple_html_tag(html_tag: str, child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        if child_block:
            return f"<{html_tag}>{rich_text}</{html_tag}>{child_block}"

        return f"<{html_tag}>{rich_text}</{html_tag}>"

    # Block type bulleted_list_item to HTML
    async def bulleted_list_item(child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        if child_block:
            return f"<li>{rich_text}<ul>{child_block}</ul></li>"

        return f"<li>{rich_text}</li>"

    # Block type paragraph to HTML
    async def paragraph(child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        if child_block:
            return f"<p>{rich_text}<ul>{child_block}</ul></p>"

        if rich_text:
            return f"<p>{rich_text}</p>"

        return ""

    # Block type to_do to HTML
    async def to_do(child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        checked = CHECKED_KEY if content[CHECKED_KEY] else ""

        return f"<div><input type='checkbox' {checked}> {rich_text}</div>"

    # Block type toggle to HTML
    async def toggle(child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        if child_block:
            return f"<details><summary>{rich_text}</summary>{child_block}</details>"

        return f"<details><summary>{rich_text}</summary></details>"

    # Block type callout to HTML
    async def callout(child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        if child_block:
            return f"<div class='callout'>{rich_text}<ul>{child_block}</ul></div>"

        return f"<div class='callout'>{rich_text}</div>"

    # Block type image to HTML
    async def image(child_block: Optional[str] = None) -> str:
        if content[TYPE_KEY] == EXTERNAL_KEY:
            image_url = content[EXTERNAL_KEY][URL_KEY]
        else:
            image_url = content[FILE_KEY][URL_KEY]

        return f"<img src='{image_url}' alt='Image'>"

    # Block type video to HTML
    async def video(child_block: Optional[str] = None) -> str:
        if content[TYPE_KEY] == EXTERNAL_KEY:
            video_url = content[EXTERNAL_KEY][URL_KEY]
        else:
            video_url = content[FILE_KEY][URL_KEY]

        return f"<video controls src='{video_url}'></video>"

    # Block type file to HTML
    async def file(child_block: Optional[str] = None) -> str:
        if content[TYPE_KEY] == EXTERNAL_KEY:
            file_url = content[EXTERNAL_KEY][URL_KEY]
        else:
            file_url = content[FILE_KEY][URL_KEY]

        return f"<a href='{file_url}'>{content[NAME_KEY]}</a>"

    # Block type pdf to HTML
    async def pdf(child_block: Optional[str] = None) -> str:
        if content[TYPE_KEY] == EXTERNAL_KEY:
            pdf_url = content[EXTERNAL_KEY][URL_KEY]
        else:
            pdf_url = content[FILE_KEY][URL_KEY]

        return f"<embed src='{pdf_url}' type='application/pdf' width='100%' height='600px' />"

    # Block type table to HTML
    async def table(child_block: Optional[str] = None) -> str:
        if child_block:
            return f"<table data-width='{content[TABLE_WIDTH_KEY]}' data-column-header='{content[HAS_COLUMN_HEADER_KEY]}' data-row-header='{content[HAS_ROW_HEADER_KEY]}'>{child_block}</table>"

        return f"<table data-width='{content[TABLE_WIDTH_KEY]}' data-column-header='{content[HAS_COLUMN_HEADER_KEY]}' data-row-header='{content[HAS_ROW_HEADER_KEY]}'></table>"

    # Block type table_row to HTML
    async def table_row(child_block: Optional[str] = None) -> str:
        cells = content[CELLS_KEY]

        row_html = "<tr>"

        for cell in cells:
            cell_content = "".join([text[PLAIN_TEXT_KEY] for text in cell])
            row_html += f"<td>{cell_content}</td>"

        row_html += "</tr>"

        return row_html

    # Block type synced_block to HTML
    async def synced_block(child_block: Optional[str] = None) -> str:
        if child_block:
            return f"<div class='synced-block'>{child_block}</div>"

        return "<div class='synced-block'></div>"

    # Block type code to HTML
    async def code(child_block: Optional[str] = None) -> str:
        rich_text = await handle_rich_text()

        # Escape special HTML characters
        escaped_code = (
            rich_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

        return f"<pre><code>\n{escaped_code}\n</code></pre>"

    # Block type column_list to HTML
    async def column_list(child_block: Optional[str] = None) -> str:
        if child_block:
            return f"<div class='column-list'>{child_block}</div>"

        return "<div class='column-list'></div>"

    # Block type column to HTML
    async def column(child_block: Optional[str] = None) -> str:
        if child_block:
            return f"<div class='column'>{child_block}</div>"

        return "<div class='column'></div>"

    # Block type child_page to HTML
    async def child_page(child_block: Optional[str] = None) -> str:
        try:
            page = await find_page(block[ID_KEY])
            page_title = block[CHILD_PAGE_KEY][TITLE_KEY]

            found_pages_databases.append(
                ChildPageOrDatabase(type=PAGE_KEY, id=block[ID_KEY])
            )

            return f"<p>{page_title}: {page[URL_KEY]}</p>"
        except APIResponseError:
            return ""

    # Block type child_database to HTML
    async def child_database(child_block: Optional[str] = None) -> str:
        try:
            database = await find_database(block[ID_KEY])
            database_title = block[CHILD_DATABASE_KEY][TITLE_KEY]

            found_pages_databases.append(
                ChildPageOrDatabase(type=DATABASE_KEY, id=block[ID_KEY])
            )

            return f"<p>{database_title}: {database[URL_KEY]}</p>"
        except APIResponseError:
            return ""

    # Block type unsupported to HTML
    async def unsupported(child_block: Optional[str] = None) -> str:
        if child_block:
            return f"{child_block}"

        return ""

    # Parse rich text content
    def parse_rich_text(rich_text: dict[str, Any]) -> str:
        if HREF_KEY in rich_text and rich_text[HREF_KEY]:
            return f"{rich_text[PLAIN_TEXT_KEY]} ({rich_text[PLAIN_TEXT_KEY]}: {rich_text[HREF_KEY]})"
        elif rich_text[ANNOTATIONS_KEY][BOLD_KEY]:
            return f"<b>{rich_text[PLAIN_TEXT_KEY]}</b>"
        elif rich_text[ANNOTATIONS_KEY][ITALIC_KEY]:
            return f"<i>{rich_text[PLAIN_TEXT_KEY]}</i>"
        elif rich_text[ANNOTATIONS_KEY][STRIKETHROUGH_KEY]:
            return f"<del>{rich_text[PLAIN_TEXT_KEY]}</del>"
        elif rich_text[ANNOTATIONS_KEY][UNDERLINE_KEY]:
            return f"<u>{rich_text[PLAIN_TEXT_KEY]}</u>"
        elif rich_text[ANNOTATIONS_KEY][CODE_KEY]:
            return f"<code>{rich_text[PLAIN_TEXT_KEY]}</code>"

        return str(rich_text[PLAIN_TEXT_KEY])

    # Get rich text content and children content
    async def handle_rich_text() -> str:
        paragraph_html_blocks = []

        for text in content[RICH_TEXT_KEY]:
            if text[TYPE_KEY] == TEXT_KEY:
                paragraph_html_blocks.append(parse_rich_text(text))
            else:
                html_child_block, pages_databases = await convert_page_block_to_html(
                    block=text,
                    found_pages_databases=found_pages_databases,
                    should_break_line=False,
                )

                paragraph_html_blocks.append(html_child_block)

        rich_texts = "".join([html for html in paragraph_html_blocks])

        if (
            ICON_KEY in content
            and content[ICON_KEY]
            and content[ICON_KEY][TYPE_KEY] == EMOJI_KEY
        ):
            return f"{content[ICON_KEY][EMOJI_KEY]} {rich_texts}"

        return rich_texts

    # Check if the block has children content
    async def get_child_block_content() -> str | None:
        if HAS_CHILDREN_KEY in block and block[HAS_CHILDREN_KEY]:
            try:
                children_results = await get_page_blocks(block[ID_KEY])

                html_blocks = []

                for child in children_results:
                    html_block, pages_databases = await convert_page_block_to_html(
                        block=child, found_pages_databases=found_pages_databases
                    )

                    html_blocks.append(html_block)

                return "".join(html_blocks)
            except APIResponseError:
                return None
        return None

    # Supported block types and their corresponding HTML transformation methods
    block_type_to_html = {
        "paragraph": paragraph,
        "heading_1": heading_1,
        "heading_2": heading_2,
        "heading_3": heading_3,
        "bulleted_list_item": bulleted_list_item,
        "numbered_list_item": numbered_list_item,
        "quote": quote,
        "template": template,
        "divider": divider,
        "to_do": to_do,
        "toggle": toggle,
        "callout": callout,
        "image": image,
        "video": video,
        "file": file,
        "pdf": pdf,
        "bookmark": bookmark,
        "embed": embed,
        "equation": equation,
        "table": table,
        "table_row": table_row,
        "synced_block": synced_block,
        "mention": mention,
        "link_to_page": link_to_page,
        "link_preview": link_preview,
        "child_page": child_page,
        "child_database": child_database,
        "code": code,
        "column_list": column_list,
        "column": column,
        "unsupported": unsupported,
    }

    # "breadcrumb"

    # Check if the current block has children content
    child_block_html = await get_child_block_content()

    # Get the HTML transformation of the current block
    html_result = await block_type_to_html.get(block[TYPE_KEY], unsupported)(
        child_block_html
    )

    if html_result and html_result != "":
        # Return the HTML transformation of the block type
        return (
            f"{"<br>" if should_break_line else ""}{html_result}",
            found_pages_databases,
        )

    return "", found_pages_databases


# Transforms a database block into HTML
def convert_database_block_to_html(property_title: str, block: dict[str, Any]) -> str:
    """
    Transforms a database block into HTML
    :param property_title: Property title
    :param block: Notion database block
    :return: HTML block
    """

    logger.debug("Converting a database block to HTML")

    # Get the content of the block
    content = block[block[TYPE_KEY]]

    # Block type title to HTML
    def title() -> str:
        block_text = "".join([entry[PLAIN_TEXT_KEY] for entry in content])
        return f"<p><b>{property_title}</b>: {block_text}</p>" if block_text else ""

    # Block type rich_text to HTML
    def rich_text() -> str:
        block_text = "".join([text[PLAIN_TEXT_KEY] for text in content])
        return f"<p><b>{property_title}</b>: {block_text}</p>" if block_text else ""

    # Block type multi_select to HTML
    def multi_select() -> str:
        block_text = ", ".join([entry[NAME_KEY] for entry in content])
        return f"<p><b>{property_title}</b>: {block_text}</p>" if block_text else ""

    # Block type select to HTML
    def select() -> str:
        return (
            f"<p><b>{property_title}</b>: {content[NAME_KEY]}</p>"
            if content and NAME_KEY in content
            else ""
        )

    # Block type status to HTML
    def status() -> str:
        return (
            f"<p><b>{property_title}</b>: {content[NAME_KEY]}</p>"
            if content and NAME_KEY in content
            else ""
        )

    # Block type unique_id to HTML
    def unique_id() -> str:
        return f"<p><b>{property_title}</b>: {content[NUMBER_KEY]}</p>"

    # Block type date to HTML
    def date() -> str:
        return (
            f"<p><b>{property_title}</b>: {content[START_DATE_KEY]}</p>"
            if content and START_DATE_KEY in content
            else ""
        )

    # Block type checkbox to HTML
    def checkbox() -> str:
        return f"<p><b>{property_title}</b>: {"Yes" if content and CHECKED_KEY in content and content[CHECKED_KEY] else "No"}</p>"

    # Block type url to HTML
    def url() -> str:
        return f"<p><b>{property_title}</b>: <a href='{content}'>{content}</a></p>"

    # Block type number to HTML
    def number() -> str:
        return f"<p><b>{property_title}</b>: {content}</p>" if content else ""

    # Block type created_time to HTML
    def created_time() -> str:
        return f"<p><b>{property_title}</b>: {content}</p>" if content else ""

    # Block type formula to HTML
    def formula() -> str:
        return f"<p><b>{property_title}</b>: {content}</p>" if content else ""

    # Block type unsupported to HTML
    def unsupported() -> str:
        return ""

    # Supported database block types and their corresponding HTML transformation methods
    block_type_to_html = {
        "rich_text": rich_text,
        "status": status,
        "select": select,
        "multi_select": multi_select,
        "title": title,
        "unique_id": unique_id,
        "date": date,
        "checkbox": checkbox,
        "url": url,
        "number": number,
        "created_time": created_time,
        "formula": formula,
        "unsupported": unsupported,
    }

    # Return the HTML transformation of the block type
    return block_type_to_html.get(block[TYPE_KEY], unsupported)()
