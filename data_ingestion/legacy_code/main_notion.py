from dataclasses import dataclass  
from datetime import datetime  
import os  
import structlog  
from typing import Any, Optional, Tuple, List  
from notion_client import AsyncClient, APIResponseError  
from dotenv import load_dotenv  
from enum import Enum  
import asyncio  
import json
  
# Load environment variables  
load_dotenv()  
  
# Initialize logger  
logger = structlog.get_logger("notion")  
  
# Initialize Notion client  
notion = AsyncClient(auth=os.getenv('NOTION_TOKEN'))  
  
# Define the RagSource enum  
class RagSource(Enum):  
    NOTION = "NOTION"  
    INTERCOM = "INTERCOM"  
  
@dataclass  
class ChildPageOrDatabase:  
    type: str  
    id: str  
  
# Fetches a page and its child pages as HTML  
async def get_notion_page_tree_as_html(root_page_id: str) -> List[str]:  
    """Fetches a page and its child pages as HTML"""  
    logger.info("Fetching a page and its child pages", page_id=root_page_id)  
    notion_pages = await get_notion_pages(root_page_id)  
    logger.info("Fetched a page and its child pages", page_id=root_page_id, size=len(notion_pages))  
      
    # Convert the page and its child pages to HTML  
    notion_pages_as_html = [notion_page['html'] for notion_page in notion_pages]  
    logger.info("Converted a page and its child pages to HTML", page_id=root_page_id, size=len(notion_pages_as_html))  
    return notion_pages_as_html  
  
# Fetches a single page as HTML  
async def get_notion_page_as_html(page_id: str) -> str:  
    """Fetches a single page as HTML"""  
    logger.info("Fetching a single page", page_id=page_id)  
    notion_page, _ = await get_notion_page(page_id)  
    if notion_page:  
        return notion_page['html']  
    return ""  
  
# Fetches a page and its child pages  
async def get_notion_pages(page_id: str, notion_pages: Optional[List] = None) -> List:  
    """Fetches a page and its child pages"""  
    if notion_pages is None:  
        notion_pages = []  
      
    notion_page, child_pages_databases = await get_notion_page(page_id)  
    if notion_page:  
        notion_pages.append(notion_page)  
        child_pages = [page for page in child_pages_databases if page.type == "page"]  
        child_databases = [database for database in child_pages_databases if database.type == "database"]  
          
        for database in child_databases:  
            database_pages = await get_database_pages(database.id)  
            child_pages.extend(database_pages)  
          
        for page in child_pages:  
            await get_notion_pages(page.id, notion_pages)  
    return notion_pages  
  
# Fetches a page by its id from Notion  
async def find_page(page_id: str) -> Any:  
    """Fetches a page by its id from Notion"""  
    logger.info("Fetching a page", page_id=page_id)  
    return await notion.pages.retrieve(page_id=page_id)  
  
# Fetches a database by its id from Notion  
async def find_database(database_id: str) -> Any:  
    """Fetches a database by its id from Notion"""  
    logger.info("Fetching a database", database_id=database_id)  
    return await notion.databases.retrieve(database_id=database_id)  
  
# Fetches the database child pages  
async def get_database_pages(database_id: str) -> List[ChildPageOrDatabase]:  
    """Converts a database id into a list of database pages"""  
    logger.info("Converting a database to HTML", database_id=database_id)  
    try:  
        database_entries = await get_database_entries(database_id)  
        database_pages: List[ChildPageOrDatabase] = []  
          
        for database_entry in database_entries:  
            if database_entry["object"] == "page":  
                database_pages.append(  
                    ChildPageOrDatabase(id=database_entry["id"], type="page")  
                )  
        return database_pages  
    except APIResponseError as e:  
        logger.warn("Failed to convert database to HTML", database_id=database_id, error=e)  
        return []  
  
# Gets a notion page already converted to HTML and its child pages  
async def get_notion_page(page_id: str) -> Tuple[dict, List[ChildPageOrDatabase]]:  
    """Gets a notion page already converted to HTML and its child pages"""  
    logger.info("Getting a notion page", page_id=page_id)  
    page = await find_page(page_id)  
    if "in_trash" in page and page["in_trash"]:  
        return None, []  
      
    blocks = await get_page_blocks(page_id)  
    found_html_blocks = []  
    found_pages_databases = []  
      
    for block in blocks:  
        html_slice, child_pages_databases = await convert_page_block_to_html(block)  
        found_html_blocks.append(html_slice)  
        found_pages_databases.extend(child_pages_databases)  
      
    html_content = "".join(found_html_blocks)  
    page_title = get_page_name(page)  
    properties_html = None  
      
    if page["parent"]["type"] == "database_id":  
        property_names = page["properties"].keys()  
        properties_html = "".join(  
            [convert_database_block_to_html(prop, page["properties"][prop]) for prop in property_names]  
        )  
      
    page_html = (f"<h1>{page_title}</h1>{properties_html}<hr>{html_content}"  
                 if properties_html else f"<h1>{page_title}</h1>{html_content}")  
      
    return {  
        'id': page_id,  
        'title': page_title,  
        'last_edited_time': page["last_edited_time"],  
        'url': page["url"],  
        'html': page_html,  
    }, found_pages_databases  
  
def get_page_name(page: dict[str, Any]) -> str:  
    """Finds the title of a page"""  
    if page["parent"]["type"] == "database_id":  
        title_property = next(  
            (property_key  
             for property_key in page["properties"].keys()  
             if page["properties"][property_key]["type"] == "title"),  
            None,  
        )  
        page_title = "".join(  
            [text["plain_text"]  
             for text in page["properties"][title_property]["title"]]  
        )  
    else:  
        page_title = "".join(  
            [text["plain_text"]  
             for text in page["properties"]["title"]["title"]]  
        )  
    return page_title  
  
# Recursively fetches all the content of a page  
async def get_page_blocks(page_id: str, cursor: Optional[str] = None, blocks: Optional[List[Any]] = None) -> List[dict[str, Any]]:  
    """Recursively fetches all the content blocks of a page"""  
    logger.debug("Fetching page blocks", page_id=page_id)  
    if blocks is None:  
        blocks = []  
    try:  
        response = await notion.blocks.children.list(block_id=page_id, start_cursor=cursor, page_size=100)  
        blocks.extend(response.get("results", []))  
        next_cursor = response.get("next_cursor")  
        if next_cursor:  
            return await get_page_blocks(page_id, cursor=next_cursor, blocks=blocks)  
    except APIResponseError as e:  
        logger.error("Failed to fetch page blocks", page_id=page_id, error=e)  
        return []  
    return blocks  
  
# Recursively fetches all the content of a database  
async def get_database_entries(database_id: str, cursor: Optional[str] = None, database_entries: Optional[List[Any]] = None) -> List[dict[str, Any]]:  
    """Recursively fetches all the content entries of a database"""  
    logger.debug("Fetching database entries", database_id=database_id)  
    if database_entries is None:  
        database_entries = []  
    response = await notion.databases.query(database_id=database_id, filter={"or": []}, sorts=[], start_cursor=cursor, page_size=100)  
    database_entries.extend(response.get("results", []))  
    next_cursor = response.get("next_cursor")  
    if next_cursor:  
        return await get_database_entries(database_id, cursor=next_cursor, database_entries=database_entries)  
    return database_entries  
  
# Transforms a page block into HTML  
async def convert_page_block_to_html(block: dict[str, Any], found_pages_databases: Optional[List[ChildPageOrDatabase]] = None, should_break_line: Optional[bool] = True) -> Tuple[str, List[ChildPageOrDatabase]]:  
    """Transforms a page block into HTML"""  
    logger.debug("Converting a page block to HTML")  
    if found_pages_databases is None:  
        found_pages_databases = []  
    content = block[block["type"]]  
      
    # Block type to HTML conversion functions  
    async def heading_1(child_block: Optional[str] = None) -> str:  
        return await simple_html_tag("h2", child_block)  
  
    async def heading_2(child_block: Optional[str] = None) -> str:  
        return await simple_html_tag("h3", child_block)  
  
    async def heading_3(child_block: Optional[str] = None) -> str:  
        return await simple_html_tag("h4", child_block)  
  
    async def quote(child_block: Optional[str] = None) -> str:  
        return await simple_html_tag("blockquote", child_block)  
  
    async def numbered_list_item(child_block: Optional[str] = None) -> str:  
        return await bulleted_list_item(child_block)  
  
    async def divider(child_block: Optional[str] = None) -> str:  
        return "<hr>"  
  
    async def bookmark(child_block: Optional[str] = None) -> str:  
        return f"<p>Bookmark: {content['url']}</p>"  
  
    async def embed(child_block: Optional[str] = None) -> str:  
        return f"<iframe src='{content['url']}'></iframe>"  
  
    async def equation(child_block: Optional[str] = None) -> str:  
        return f"<div>{content['expression']}</div>"  
  
    async def link_to_page(child_block: Optional[str] = None) -> str:  
        title = None  
        url = None  
        if content["type"] == "page_id":  
            page = await find_page(content["page_id"])  
            title = get_page_name(page)  
            url = page["url"]  
        elif content["type"] == "database_id":  
            database = await find_database(content["database_id"])  
            title = database["url"]  
            url = database["url"]  
        if title and url:  
            return f"<p>{title}: {url}</p>"  
        return ""  
  
    async def simple_html_tag(html_tag: str, child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        if child_block:  
            return f"<{html_tag}>{rich_text}</{html_tag}>{child_block}"  
        return f"<{html_tag}>{rich_text}</{html_tag}>"  
  
    async def bulleted_list_item(child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        if child_block:  
            return f"<li>{rich_text}<ul>{child_block}</ul></li>"  
        return f"<li>{rich_text}</li>"  
  
    async def paragraph(child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        if child_block:  
            return f"<p>{rich_text}<ul>{child_block}</ul></p>"  
        if rich_text:  
            return f"<p>{rich_text}</p>"  
        return ""  
  
    async def to_do(child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        checked = "checked" if content["checked"] else ""  
        return f"<div><input type='checkbox' {checked}> {rich_text}</div>"  
  
    async def toggle(child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        if child_block:  
            return f"<details><summary>{rich_text}</summary>{child_block}</details>"  
        return f"<details><summary>{rich_text}</summary></details>"  
  
    async def callout(child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        if child_block:  
            return f"<div class='callout'>{rich_text}<ul>{child_block}</ul></div>"  
        return f"<div class='callout'>{rich_text}</div>"  
  
    async def image(child_block: Optional[str] = None) -> str:  
        image_url = content["external"]["url"] if content["type"] == "external" else content["file"]["url"]  
        return f"<img src='{image_url}' alt='Image'>"  
  
    async def video(child_block: Optional[str] = None) -> str:  
        video_url = content["external"]["url"] if content["type"] == "external" else content["file"]["url"]  
        return f"<video controls src='{video_url}'></video>"  
  
    async def file(child_block: Optional[str] = None) -> str:  
        file_url = content["external"]["url"] if content["type"] == "external" else content["file"]["url"]  
        return f"<a href='{file_url}'>{content['name']}</a>"  
  
    async def pdf(child_block: Optional[str] = None) -> str:  
        pdf_url = content["external"]["url"] if content["type"] == "external" else content["file"]["url"]  
        return f"<embed src='{pdf_url}' type='application/pdf' width='100%' height='600px' />"  
  
    async def table(child_block: Optional[str] = None) -> str:  
        return f"<table data-width='{content['table_width']}' data-column-header='{content['has_column_header']}' data-row-header='{content['has_row_header']}'>{child_block if child_block else ''}</table>"  
  
    async def table_row(child_block: Optional[str] = None) -> str:  
        cells = content["cells"]  
        row_html = "<tr>"  
        for cell in cells:  
            cell_content = "".join([text["plain_text"] for text in cell])  
            row_html += f"<td>{cell_content}</td>"  
        row_html += "</tr>"  
        return row_html  
  
    async def code(child_block: Optional[str] = None) -> str:  
        rich_text = await handle_rich_text()  
        escaped_code = rich_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")  
        return f"<pre><code>\n{escaped_code}\n</code></pre>"  
  
    async def unsupported(child_block: Optional[str] = None) -> str:  
        return child_block if child_block else ""  
  
    def parse_rich_text(rich_text: dict[str, Any]) -> str:  
        if "href" in rich_text and rich_text["href"]:  
            return f"{rich_text['plain_text']} ({rich_text['plain_text']}: {rich_text['href']})"  
        elif rich_text["annotations"]["bold"]:  
            return f"<b>{rich_text['plain_text']}</b>"  
        elif rich_text["annotations"]["italic"]:  
            return f"<i>{rich_text['plain_text']}</i>"  
        elif rich_text["annotations"]["strikethrough"]:  
            return f"<del>{rich_text['plain_text']}</del>"  
        elif rich_text["annotations"]["underline"]:  
            return f"<u>{rich_text['plain_text']}</u>"  
        elif rich_text["annotations"]["code"]:  
            return f"<code>{rich_text['plain_text']}</code>"  
        return str(rich_text["plain_text"])  
  
    async def handle_rich_text() -> str:  
        paragraph_html_blocks = []  
        for text in content["rich_text"]:  
            if text["type"] == "text":  
                paragraph_html_blocks.append(parse_rich_text(text))  
            else:  
                html_child_block, _ = await convert_page_block_to_html(block=text, found_pages_databases=found_pages_databases, should_break_line=False)  
                paragraph_html_blocks.append(html_child_block)  
        rich_texts = "".join(paragraph_html_blocks)  
        if "icon" in content and content["icon"] and content["icon"]["type"] == "emoji":  
            return f"{content['icon']['emoji']} {rich_texts}"  
        return rich_texts  
  
    async def get_child_block_content() -> str:  
        if "has_children" in block and block["has_children"]:  
            try:  
                children_results = await get_page_blocks(block["id"])  
                html_blocks = []  
                for child in children_results:  
                    html_block, _ = await convert_page_block_to_html(block=child, found_pages_databases=found_pages_databases)  
                    html_blocks.append(html_block)  
                return "".join(html_blocks)  
            except APIResponseError:  
                return ""  
        return ""  
  
    block_type_to_html = {  
        "paragraph": paragraph,  
        "heading_1": heading_1,  
        "heading_2": heading_2,  
        "heading_3": heading_3,  
        "bulleted_list_item": bulleted_list_item,  
        "numbered_list_item": numbered_list_item,  
        "quote": quote,  
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
        "code": code,  
        "unsupported": unsupported,  
    }  
  
    child_block_html = await get_child_block_content()  
    html_result = await block_type_to_html.get(block["type"], unsupported)(child_block_html)  
    if html_result and html_result != "":  
        return (f"{'<br>' if should_break_line else ''}{html_result}", found_pages_databases)  
    return "", found_pages_databases  
  
# Transforms a database block into HTML  
def convert_database_block_to_html(property_title: str, block: dict[str, Any]) -> str:  
    """Transforms a database block into HTML"""  
    logger.debug("Converting a database block to HTML")  
    content = block[block["type"]]  
  
    def title() -> str:  
        block_text = "".join([entry["plain_text"] for entry in content])  
        return f"<p><b>{property_title}</b>: {block_text}</p>" if block_text else ""  
  
    def rich_text() -> str:  
        block_text = "".join([text["plain_text"] for text in content])  
        return f"<p><b>{property_title}</b>: {block_text}</p>" if block_text else ""  
  
    def multi_select() -> str:  
        block_text = ", ".join([entry["name"] for entry in content])  
        return f"<p><b>{property_title}</b>: {block_text}</p>" if block_text else ""  
  
    def select() -> str:  
        return (f"<p><b>{property_title}</b>: {content['name']}</p>" if content and "name" in content else "")  
  
    def status() -> str:  
        return (f"<p><b>{property_title}</b>: {content['name']}</p>" if content and "name" in content else "")  
  
    def unique_id() -> str:  
        return f"<p><b>{property_title}</b>: {content['number']}</p>"  
  
    def date() -> str:  
        return (f"<p><b>{property_title}</b>: {content['start']}</p>" if content and "start" in content else "")  
  
    def checkbox() -> str:  
        return f"<p><b>{property_title}</b>: {'Yes' if content and 'checked' in content and content['checked'] else 'No'}</p>"  
  
    def url() -> str:  
        return f"<p><b>{property_title}</b>: <a href='{content}'>{content}</a></p>"  
  
    def number() -> str:  
        return f"<p><b>{property_title}</b>: {content}</p>" if content else ""  
  
    def created_time() -> str:  
        return f"<p><b>{property_title}</b>: {content}</p>" if content else ""  
  
    def formula() -> str:  
        return f"<p><b>{property_title}</b>: {content}</p>" if content else ""  
  
    def unsupported() -> str:  
        return ""  
  
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
  
    return block_type_to_html.get(block["type"], unsupported)()  

  
async def main():  
    root_page_id = "0bc3d93e-d27e-48dd-a393-8ba52bfc93b9"  
    processed_data = []  

    try:  
        # Fetch the Notion page and its child pages as HTML  
        html_content = await get_notion_page_tree_as_html(root_page_id)  
        print("total number of pages", len(html_content))
        # Print out the retrieved HTML content  
        for i, html in enumerate(html_content, start=1):  
            print(f"Page {i} HTML content: {html[:100]}...")
            # Add to processed data  
            processed_data.append({  
                "content": html  
            })  
  
        # Write to JSONL file  
        os.makedirs('output', exist_ok=True)  
        output_file = 'output/notion_content.jsonl'  
        logger.info(f"Writing processed data to {output_file}")  
        with open(output_file, 'w') as f:  
            for entry in processed_data:  
                json.dump(entry, f)  
                f.write('\n')  
  
      
    except Exception as e:  
        logger.error("An error occurred while fetching the Notion page", error=str(e))  
  
if __name__ == "__main__":  
    asyncio.run(main())  