from datetime import datetime

import aiohttp
import json
import structlog

from typing import Any, Optional

from langchain_core.documents import Document

from customer_care_agent.model.intercom_page import IntercomPage
from customer_care_agent.model.product_agent_info import RagSource
from customer_care_agent.services import async_get
from customer_care_agent.utils.bs_html_loader import CustomBSHTMLLoader

logger = structlog.get_logger("intercom")


async def get_intercom_page_tree_as_documents(
    collection_ids: list[str], secret: str
) -> list[Document]:
    """
    Fetches all Intercom pages and collections and returns them as documents.

    :param collection_ids: The collection IDs.
    :return: A list of documents.
    """
    intercom_pages = await find_all_pages_for_collections(collection_ids, secret)

    # Convert the page and its child pages to documents
    intercom_pages_as_documents = [
        CustomBSHTMLLoader(
            id=intercom_page.id,
            content=intercom_page.html,
            title=intercom_page.title,
            source=intercom_page.url,
            timestamp=datetime.now().isoformat(),
            integration=str(RagSource.INTERCOM),
            visibility="PUBLIC",
            use_break_line=False,
        ).load()
        for intercom_page in intercom_pages
    ]

    # Flatten the list of documents
    documents = [doc for sublist in intercom_pages_as_documents for doc in sublist]

    for doc in documents:
        doc.metadata["visibility"] = "PUBLIC"

    logger.info(
        "Converted a page and its child pages to documents",
        collection_ids=collection_ids,
        size=len(documents),
    )

    return documents


async def find_all_pages_for_collections(
    collection_ids: list[str], secret: str
) -> list[IntercomPage]:
    """
    Fetches all pages for a given list of collection parents.

    :param collection_ids: The collection IDs.
    :return: A list of all pages.
    """
    pages = await find_all_intercom_pages(secret)
    collections = await find_all_intercom_collections(secret)

    filtered_collections = await find_all_child_intercom_collections(
        collection_ids, collections
    )
    filtered_collection_ids = [collection["id"] for collection in filtered_collections]

    return [
        page
        for page in pages
        if page.parent_id in filtered_collection_ids or page.id in collection_ids
    ]


async def find_all_child_intercom_collections(
    collection_ids: list[str],
    all_collections: list[dict[str, Any]],
    collections: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """
    Fetches all child Intercom collections recursively.

    :param collection_ids: The parent IDs.
    :param all_collections: All collections to search through.
    :param collections: Accumulated child collections.
    :return: A list of all child collections.
    """

    if collections is None:
        collections = []

    child_collection_ids = []

    for collection in all_collections:
        if collection["id"] in collection_ids:
            collections.append(collection)
        if collection["parent_id"] in collection_ids:
            child_collection_ids.append(collection["id"])

    if child_collection_ids:
        await find_all_child_intercom_collections(
            child_collection_ids, all_collections, collections
        )

    return collections


async def find_all_intercom_collections(secret: str) -> list[dict[str, Any]]:
    """
    Fetches all Intercom collections.

    :return: The response text from the API or an error message.
    """
    page = 1
    collections = []

    while True:
        response = await find_intercom_collections(page, secret)
        collections.extend(response["data"])

        if int(response["pages"]["total_pages"]) == page:
            break

        page += 1

    return collections


async def find_intercom_collections(page: int, secret: str) -> Any:
    """
    Fetches all Intercom collections.

    :param page: The page number.
    :param secret: The Intercom API secret.
    :return: The response text from the API or an error message.
    """
    url = f"https://api.intercom.io/help_center/collections?page={page}&per_page=200"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {secret}",
        "Intercom-Version": "2.10",
    }

    try:
        response = await async_get(url, headers)
        return json.loads(response)
    except aiohttp.ClientResponseError as http_err:
        raise ValueError(f"HTTP error occurred: {http_err}")
    except Exception as err:
        raise ValueError(f"An error occurred: {err}")


async def find_all_intercom_pages(secret: str) -> list[IntercomPage]:
    """
    Fetches all Intercom pages.

    :return: The response text from the API or an error message.
    """
    page = 1
    pages = []

    while True:
        response = await find_intercom_pages(page, secret)
        pages.extend(response["data"])

        if int(response["pages"]["total_pages"]) == page:
            break

        page += 1

    return [
        IntercomPage(
            id=page["id"],
            html=page["body"],
            url=page["url"],
            title=page["title"],
            last_edited_time=datetime.fromtimestamp(page["updated_at"]).isoformat(),
            parent_id=str(page["parent_id"]),
        )
        for page in pages
        if page["state"] == "published"
    ]


async def find_intercom_pages(page: int, secret: str) -> Any:
    """
    Fetches all Intercom pages.

    :param page: The page number.
    :param secret: The Intercom API secret.
    :return: The response text from the API or an error message.
    """
    url = f"https://api.intercom.io/articles?page={page}&per_page=250&type=pages"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {secret}",
        "Intercom-Version": "2.10",
    }

    try:
        response = await async_get(url, headers)
        return json.loads(response)
    except aiohttp.ClientResponseError as http_err:
        raise ValueError(f"HTTP error occurred: {http_err}")
    except Exception as err:
        raise ValueError(f"An error occurred: {err}")
