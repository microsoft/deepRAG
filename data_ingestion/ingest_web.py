import os  
import re  
import json  
import threading  
import concurrent.futures  
from utils import extract_content_from_url, extract_title, get_image_description  
  
def replace_image_urls_with_descriptions(extracted_content, image_urls, get_image_description_func=get_image_description):  
    with concurrent.futures.ThreadPoolExecutor() as executor:  
        image_descriptions = list(executor.map(get_image_description_func, image_urls))  
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
  
def process_single_url(url, processed_urls, current_depth, depth_limit, lock,   
                       extract_content_func=extract_content_from_url, extract_title_func=extract_title, get_image_description_func=get_image_description):  
    if current_depth > depth_limit:  
        print(f"Depth limit reached for {url}. Skipping further processing.")  
        return None  
  
    with lock:  
        if url in processed_urls:  
            print(f"URL {url} already processed. Skipping.")  
            return None  
  
    extracted_content = extract_content_func(url)  
    if extracted_content is None:  
        return None  
  
    title = extract_title_func(extracted_content)  
    image_urls = re.findall(r'\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif)(?:\?.*?)?)\)', extracted_content)  
    updated_content = replace_image_urls_with_descriptions(extracted_content, image_urls, get_image_description_func)  
  
    with lock:  
        processed_urls.add(url)  
  
    return {"url": url, "title": title, "content": updated_content}  
  
def process_urls_and_write_to_file(main_url, output_file, max_entries, depth_limit,   
                                   extract_content_func=extract_content_from_url, extract_title_func=extract_title, get_image_description_func=get_image_description):  
    processed_entries = 0  
    urls_to_process = [(main_url, 0)]  
    processed_data = []  
    processed_urls = set()  
    lock = threading.Lock()  
  
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  
        while urls_to_process and processed_entries < max_entries:  
            print(f"Processed {processed_entries}/{max_entries} entries. Processing {len(urls_to_process)} URLs.")  
            futures = {  
                executor.submit(process_single_url, url, processed_urls, current_depth, depth_limit, lock, extract_content_func, extract_title_func, get_image_description_func): (url, current_depth)  
                for url, current_depth in urls_to_process[:10]  
            }  
            urls_to_process = urls_to_process[10:]  
  
            for future in concurrent.futures.as_completed(futures):  
                result = future.result()  
                if result is None:  
                    continue  
  
                processed_data.append(result)  
                processed_entries += 1  
  
                reference_urls = extract_reference_urls(result['content'])  
                with lock:  
                    for ref_url in reference_urls:  
                        if processed_entries < max_entries and (ref_url not in processed_urls):  
                            urls_to_process.append((ref_url, futures[future][1] + 1))  
                        if processed_entries >= max_entries:  
                            break  
  
    os.makedirs(os.path.dirname(output_file), exist_ok=True)  
  
    with open(output_file, 'w') as f:  
        for entry in processed_data:  
            json.dump(entry, f)  
            f.write('\n')  
    
# Example Usage  
if __name__ == "__main__":  
    # Default values  
    main_article_url = 'https://intercom.help/sixfold/en/articles/6023034-visibility-control-center-for-shippers-lsps'  
    output_file_name = 'processed_data/extracted_content.jsonl'  
    DEPTH_LIMIT = 10  
    MAX_ENTRIES = 20  
      
    process_urls_and_write_to_file(  
        main_url=main_article_url,  
        output_file=output_file_name,  
        depth_limit=DEPTH_LIMIT,  
        max_entries=MAX_ENTRIES  
    )  