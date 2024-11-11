import os  
import json  
import asyncio  
import logging  
from datetime import datetime  
from typing import Any, Optional, List  
import aiohttp  
from dotenv import load_dotenv  
from dataclasses import dataclass, asdict  
from utils import extract_content_from_url, get_image_description  
import concurrent.futures  
import re

# Load environment variables  
load_dotenv()  
secret = os.getenv("INTERCOM_TOKEN")  
  
# Configure logger  
logging.basicConfig(level=logging.DEBUG)  
logger = logging.getLogger(__name__)  
  
# Define the root collection IDs  
ROOT_COLLECTION_IDS = [  
    "6014082", "5922241", "6023034", "5913544",  
    "5885750", "5913563", "2509158", "2509162", "2519539"  
]  
  
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
  
async def get_intercom_html_content(collection_ids: List[str], secret: str) -> List[dict[str, Any]]:  
    """Fetches all Intercom pages and returns their HTML content."""  
    intercom_pages = await find_all_pages_for_collections(collection_ids, secret)  
  
    # Collect the HTML content, convert to Markdown, and replace image URLs with descriptions  
    intercom_html_content = []  
    for page in intercom_pages:  
        html_content = page.html  
        markdown_content = extract_content_from_url(html_data=html_content)  
        markdown_content_no_images = replace_image_urls_with_descriptions(markdown_content)  
  
        intercom_html_content.append({  
            "id": page.id,  
            "html": page.html,  
            "markdown": markdown_content_no_images,  
            "title": page.title,  
            "url": page.url,  
            "timestamp": datetime.now().isoformat(),  
        })  
  
    logger.info(  
        "Collected HTML content from pages. Collection IDs: %s, Size: %d",  
        collection_ids, len(intercom_html_content)  
    )  
    return intercom_html_content  
  
def replace_image_urls_with_descriptions(content: str) -> str:  
    logger.debug("Replacing image URLs with descriptions")  
    image_urls = re.findall(r'<img src=\'(https?://.*?\.(?:png|jpg|jpeg|gif)(?:\?.*?)?)\'', content)  
    with concurrent.futures.ThreadPoolExecutor() as executor:  
        image_descriptions = list(executor.map(get_image_description, image_urls))  
        for image_url, description in zip(image_urls, image_descriptions):  
            content = content.replace(image_url, description)  
    return content  
  
async def find_all_pages_for_collections(collection_ids: List[str], secret: str) -> List[IntercomPage]:  
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
    collection_ids: List[str],  
    all_collections: List[dict[str, Any]],  
    collections: Optional[List[dict[str, Any]]] = None,  
) -> List[dict[str, Any]]:  
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
  
async def find_all_intercom_collections(secret: str) -> List[dict[str, Any]]:  
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
  
async def find_all_intercom_pages(secret: str) -> List[IntercomPage]:  
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
    with open('processed_data/intercom_pages.jsonl', 'w') as jsonl_file:  
        for page in html_content:  
            jsonl_file.write(json.dumps(page) + '\n')  
      
    logger.info("Saved HTML content to intercom_pages.jsonl")  
  
# Run the main function  
if __name__ == "__main__":  
    asyncio.run(main())  