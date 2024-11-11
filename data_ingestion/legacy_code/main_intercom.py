import aiohttp  
import asyncio  
import json  
from typing import Any, List  
from dotenv import load_dotenv  
import os

  
async def async_get(url: str, headers: dict) -> str:  
    """Perform an asynchronous GET request."""  
    async with aiohttp.ClientSession() as session:  
        async with session.get(url, headers=headers) as response:  
            response.raise_for_status()  
            return await response.text()  
  
async def find_intercom_pages(page: int, secret: str) -> Any:  
    """Fetches all Intercom pages for a specific page number."""  
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
  
async def find_all_intercom_pages(secret: str) -> List[dict]:  
    """Fetches all Intercom pages."""  
    page = 1  
    pages = []  
    while True:  
        response = await find_intercom_pages(page, secret)  
        pages.extend(response["data"])  
        if int(response["pages"]["total_pages"]) == page:  
            break  
        page += 1  
    return pages  
  
async def fetch_intercom_data(secret: str):  
    """Fetch and print Intercom page data."""  
    pages = await find_all_intercom_pages(secret)  
    print("total number of pages", len(pages))
    for page in pages:  
        print(f"Title: {page['title']}")  
        print(f"URL: {page['url']}")  
        print(f"Last Edited: {page.get('updated_at')}")  
        print(f"Content Snippet: {page.get('body', '')[:100]}...")  # Print the first 100 characters  
        print("-" * 80)  
  
# Define the secret key  
# Load environment variables  
load_dotenv()  
secret = os.getenv("INTERCOM_SECRET")  
# Run the asynchronous function  
asyncio.run(fetch_intercom_data(secret))  