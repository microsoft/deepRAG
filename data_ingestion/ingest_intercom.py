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
import time

# Load environment variables  
load_dotenv()  
secret = os.getenv("INTERCOM_TOKEN")  
  
# Configure logger  
logging.basicConfig(level=logging.DEBUG)  
logger = logging.getLogger(__name__)  
  
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
  
async def process_page(page: IntercomPage, semaphore: asyncio.Semaphore) -> dict[str, Any]:  
    """Processes a single page, converting its content to Markdown and replacing image URLs."""  
    async with semaphore:  
        html_content = page.html  
        markdown_content = extract_content_from_url(html_data=html_content)  
        markdown_content_no_images = replace_image_urls_with_descriptions(markdown_content)  
  
        return {  
            "id": page.id,  
            "content": markdown_content_no_images,  
            "title": page.title,  
            "url": page.url,  
            "timestamp": datetime.now().isoformat(),  
        }  
  
async def find_and_process_all_pages(secret: str, collection_ids: List[str], concurrent_tasks) -> List[dict[str, Any]]:  
    """Finds all pages for the given collections and processes them."""  
    pages = await find_all_pages_for_collections(collection_ids, secret)  
      
    semaphore = asyncio.Semaphore(concurrent_tasks)  
    tasks = [process_page(page, semaphore) for page in pages]  
    results = await asyncio.gather(*tasks)  
      
    logger.info("Processed all pages. Total Size: %d", len(results))  
    return results  
  
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
  
  
def replace_image_urls_with_descriptions(content: str) -> str:  
    logger.debug("Replacing image URLs with descriptions")  
    image_urls = re.findall(r'\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif)(?:\?.*?)?)\)', content)  

    print("Image URLs: ", image_urls) 
    with concurrent.futures.ThreadPoolExecutor() as executor:  
        image_descriptions = list(executor.map(get_image_description, image_urls))  
        print("Image descriptions: ", image_descriptions)
        for image_url, description in zip(image_urls, image_descriptions):  
            content = content.replace(image_url, description)  
    return content  
  
  
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
        # Define the root collection IDs  
    ROOT_COLLECTION_IDS = [  
        "6014082", "5922241", "6023034", "5913544",  
        "5885750", "5913563", "2509158", "2509162", "2519539"  
    ]  
    CONCURRENT_TASKS = 60  # Control the number of concurrent tasks  
    await ingest_intercom('Road Visibility', ROOT_COLLECTION_IDS, 'intercom', CONCURRENT_TASKS)


async def ingest_intercom(product, root_collection_ids: List[str],source='intercome', concurrent_tasks=60, output_file='processed_data/intercom_pages.jsonl') -> None:

    start_time = time.time()
    # Fetch and process the HTML content from Intercom pages  
    html_content = await find_and_process_all_pages(secret, root_collection_ids,concurrent_tasks)  
  
    # Save the content to a JSONL file  
    with open(output_file, 'a') as jsonl_file:  
        for page in html_content:
            page['product'] = product
            page['source'] = source  
            jsonl_file.write(json.dumps(page) + '\n')  
  
    logger.info(f"Saved HTML content to {output_file} jsonl")  
    end_time = time.time()
    logger.info(f"Total time taken: {end_time - start_time} seconds")

# Run the main function  
if __name__ == "__main__":  
    asyncio.run(main())  