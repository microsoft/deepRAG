import os  
import json  
from datetime import datetime  
import aiohttp  
import asyncio  
import structlog  
from dotenv import load_dotenv  
from typing import Any, Optional  

import json

from dataclasses import dataclass, asdict


@dataclass
class IntercomPage:
    id: str
    url: str
    html: str
    title: str
    last_edited_time: str
    parent_id: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
  
# Load environment variables  
load_dotenv()  
secret = os.getenv("INTERCOM_TOKEN")  
  
# Configure logger  
logger = structlog.get_logger("intercom")  
  
# Define the root collection IDs  
ROOT_COLLECTION_IDS = [  
    "6014082", "5922241", "6023034", "5913544",  
    "5885750", "5913563", "2509158", "2509162", "2519539"  
]  
  
async def get_intercom_html_content(collection_ids: list[str], secret: str) -> list[dict[str, Any]]:  
    """Fetches all Intercom pages and returns their HTML content."""  
    intercom_pages = await find_all_pages_for_collections(collection_ids, secret)  
      
    # Collect the HTML content and other metadata  
    intercom_html_content = [  
        {  
            "id": intercom_page.id,  
            "html": intercom_page.html,  
            "title": intercom_page.title,  
            "url": intercom_page.url,  
            "timestamp": datetime.now().isoformat(),  
        }  
        for intercom_page in intercom_pages  
    ]  
      
    logger.info(  
        "Collected HTML content from pages",  
        collection_ids=collection_ids,  
        size=len(intercom_html_content),  
    )  
    return intercom_html_content  
  
async def find_all_pages_for_collections(collection_ids: list[str], secret: str) -> list[IntercomPage]:  
    """Fetches all pages for a given list of collection parents."""  
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
    """Fetches all child Intercom collections recursively."""  
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
    """Fetches all Intercom collections."""  
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
    """Fetches all Intercom collections."""  
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
    """Fetches all Intercom pages."""  
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
    """Fetches all Intercom pages."""  
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
  
async def async_get(url: str, headers: dict) -> str:  
    """Perform an asynchronous GET request."""  
    async with aiohttp.ClientSession() as session:  
        async with session.get(url, headers=headers) as response:  
            response.raise_for_status()  
            return await response.text()  
  
async def main():  
    # Fetch the HTML content from Intercom pages  
    html_content = await get_intercom_html_content(ROOT_COLLECTION_IDS, secret)  
      
    # Save the content to a JSONL file  
    with open('intercom_pages.jsonl', 'w') as jsonl_file:  
        for page in html_content:  
            jsonl_file.write(json.dumps(page) + '\n')  
      
    logger.info("Saved HTML content to intercom_pages.jsonl")  
  
# Run the main function  
if __name__ == "__main__":  
    asyncio.run(main())  