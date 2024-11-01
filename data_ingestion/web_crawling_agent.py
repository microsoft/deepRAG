import os  
import re  
import json  
import time  
import concurrent.futures  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from requests_html import HTMLSession  
import threading  

  
# Load environment variables  
load_dotenv()  
  
# Initialize HTML session  
session = HTMLSession()  
  
# Initialize Azure OpenAI client  
engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
processing_engine = os.getenv("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT")  
client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  
  
def extract_content_from_url(url, retries=0):  
    if retries > 1:  
        print(f"Max retries reached for {url}. Skipping.")  
        return None  # Return None if max retries exceeded  
    try:  
        r = session.get(url)  
        html_data = r.html.html  
          
        prompt = f"""  
        Extract the content from the following HTML.  
  
        ### Requirements for the output:  
        - Start with the title of the article under ### Title.  
        - Retain the original positions of hyperlinks within the content.  
        - Output the content in raw markdown format.  
        - If there are reference links in the content, output them at the end under ### References with descriptions and URLs.  
  
        ### HTML Content:  
        {html_data}  
        """  
  
        messages = [  
            {"role": "system", "content": "You are a helpful AI assistant"},  
            {"role": "user", "content": prompt}  
        ]  
  
        response = client.chat.completions.create(  
            model=engine,  
            messages=messages,  
        )  
  
        extracted_content = response.choices[0].message.content.strip()  
        return extracted_content  
  
    except Exception as e:  
        print(f"Failed to extract content from {url}: {e}")  
        time.sleep(5)  # Sleep and try again after 5 seconds  
        return extract_content_from_url(url, retries + 1)  # Retry with incremented retry count  
  
def extract_title(content):  
    title_match = re.search(r'### Title\s*(.*?)\n', content)  
    if title_match:  
        return title_match.group(1).strip()  
    return "Untitled"  
  
def get_image_description(image_url, retries=0):  
    max_retries = 2
    try:  
        response = client.chat.completions.create(  
            model=processing_engine,  
            messages=[  
                {  
                    "role": "user",  
                    "content": [  
                        {"type": "text", "text": "Describe this image"},  
                        {"type": "image_url", "image_url": {"url": image_url}}  
                    ],  
                }  
            ],  
            max_tokens=300  
        )  
        return response.choices[0].message.content.strip()  
  
    except Exception as e:  
        if retries < max_retries:  
            print(f"Failed to get image description for {image_url}: {e}. Retrying ({retries + 1}/{max_retries})...")  
            time.sleep(5)  # Wait before retrying  
            return get_image_description(image_url, retries + 1)  
        else:  
            print(f"Max retries reached for {image_url}. Skipping.")  
            return f"[Description for {image_url} not available due to error.]"  
          
def replace_image_urls_with_descriptions(extracted_content, image_urls):  
    with concurrent.futures.ThreadPoolExecutor() as executor:  
        image_descriptions = list(executor.map(get_image_description, image_urls))  
        for image_url, description in zip(image_urls, image_descriptions):  
            extracted_content = extracted_content.replace(image_url, description)  
    return extracted_content  
  
def extract_reference_urls(content):  
    references_start = content.find("### References")  
    if references_start == -1:  
        return []  
    references_content = content[references_start:]  
    reference_urls = re.findall(r'\[.*?\]\((https?://.*?)\)', references_content)  
    return [url for url in reference_urls if not '.pdf' in url.lower()]  
  
def process_single_url(url, processed_urls, current_depth, depth_limit, lock):  
    if current_depth > depth_limit:  
        print(f"Depth limit reached for {url}. Skipping further processing.")  
        return None  
  
    with lock:  
        if url in processed_urls:  
            print(f"URL {url} already processed. Skipping.")  
            return None  
  
    extracted_content = extract_content_from_url(url)  
    if extracted_content is None:  
        return None  # Skip if extraction failed after retries  
  
    title = extract_title(extracted_content)  
    image_urls = re.findall(r'\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif)(?:\?.*?)?)\)', extracted_content)  
    updated_content = replace_image_urls_with_descriptions(extracted_content, image_urls)  
  
    with lock:  
        processed_urls.add(url)  # Mark URL as processed  
  
    return {"url": url, "title": title, "content": updated_content}  
def process_urls_and_write_to_file(main_url, output_file, max_entries=300, depth_limit=10):  
    processed_entries = 0  
    urls_to_process = [(main_url, 0)]  # Tuple of URL and current depth  
    processed_data = []  
    processed_urls = set()  # Set to track processed URLs  
    lock = threading.Lock()  # Lock for thread-safe operations  
  
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  
        while urls_to_process and processed_entries < max_entries: 
            print(f"Processed {processed_entries}/{max_entries} entries. Processing {len(urls_to_process)} URLs.") 
            futures = {  
                executor.submit(process_single_url, url, processed_urls, current_depth, depth_limit, lock): (url, current_depth)  
                for url, current_depth in urls_to_process[:10]  
            }  
            urls_to_process = urls_to_process[10:]  # Limit processing to 10 URLs at a time  
  
            for future in concurrent.futures.as_completed(futures):  
                result = future.result()  
                if result is None:  
                    continue  # Skip if result is None  
  
                processed_data.append(result)  
                processed_entries += 1  
  
                # Extract reference URLs only from the "### References" section  
                reference_urls = extract_reference_urls(result['content'])  
                with lock:  
                    for ref_url in reference_urls:  
                        if processed_entries < max_entries and (ref_url not in processed_urls):  
                            urls_to_process.append((ref_url, futures[future][1] + 1))  # Increment depth  
                        if processed_entries >= max_entries:  
                            break  
  
    # Ensure the directory for the output file exists  
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  
  
    # Write the processed data to a JSON Lines file  
    with open(output_file, 'w') as f:  
        for entry in processed_data:  
            json.dump(entry, f)  
            f.write('\n')  
  
  
  
# URL of the main article  
main_article_url = 'https://intercom.help/sixfold/en/articles/6023034-visibility-control-center-for-shippers-lsps'  
# Output file name  
output_file_name = 'processed_data/extracted_content.jsonl'  

# Execute the main process with a depth limit of 10  
DEPTH_LIMIT = 10
MAX_ENTRIES = 20
process_urls_and_write_to_file(main_article_url, output_file_name, depth_limit=DEPTH_LIMIT, max_entries=MAX_ENTRIES)  