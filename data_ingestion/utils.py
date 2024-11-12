from requests_html import HTMLSession  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from selenium import webdriver  
from PIL import Image  
from selenium.webdriver.chrome.options import Options  
import time  
import os  
import re  
import json  
import os  
import uuid  
from azure.cosmos import CosmosClient  
from azure.identity import DefaultAzureCredential  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
  
import tiktoken  

  
# Load environment variables  
load_dotenv()  
  
# Initialize HTML session  
session = HTMLSession()  
  
# Initialize Azure OpenAI client  
engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
processing_engine = os.getenv("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT")  
openai_client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  
openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  

cosmos_uri = os.environ.get("COSMOS_URI")  
container_name = os.getenv("COSMOS_CONTAINER_NAME")  
cosmos_db_name = os.getenv("COSMOS_DB_NAME")  
if os.getenv("COSMOS_KEY"):
    # Configure CosmosDB client with KEY authentication  
    cosmos_key = os.environ.get("COSMOS_KEY")
    cosmos_client = CosmosClient(cosmos_uri, cosmos_key)
else:
    # Retrieve environment variables for AAD authentication  
    aad_client_id = os.getenv("AAD_CLIENT_ID")  
    aad_client_secret = os.getenv("AAD_CLIENT_SECRET")  
    aad_tenant_id = os.getenv("AAD_TENANT_ID")  
    # Configure CosmosDB client with AAD authentication  
    # Set up the DefaultAzureCredential with the client ID, client secret, and tenant ID  
    os.environ["AZURE_CLIENT_ID"] = aad_client_id  
    os.environ["AZURE_CLIENT_SECRET"] = aad_client_secret  
    os.environ["AZURE_TENANT_ID"] = aad_tenant_id  
    credential = DefaultAzureCredential()  
    cosmos_client = CosmosClient(cosmos_uri, credential=credential)  
  
cosmos_db_client = cosmos_client.get_database_client(cosmos_db_name)  
cosmos_container_client = cosmos_db_client.get_container_client(container_name)  

  
def extract_content_from_url(url=None, html_data=None, retries=0):  
    if retries > 1:  
        print(f"Max retries reached for {url}. Skipping.")  
        return None  # Return None if max retries exceeded  
    try:  
        if url:  
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
          
        response = openai_client.chat.completions.create(  
            model=processing_engine,  
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
        response = openai_client.chat.completions.create(  
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
  
def extract_website_as_image(url, output_path='stitched_screenshot.png'):  
    # Initialize the WebDriver  
    chrome_options = Options()  
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--window-size=1920,1080")  
    chrome_options.add_argument("--hide-scrollbars")  
    driver = webdriver.Chrome(options=chrome_options)  
      
    try:  
        driver.get(url)  
        time.sleep(3)  # Pause to let the page load  
          
        # Get the total height of the page  
        total_height = driver.execute_script("return document.body.scrollHeight")  
        viewport_height = driver.execute_script("return window.innerHeight")  
          
        # Create a directory to save screenshots  
        if not os.path.exists('screenshots'):  
            os.makedirs('screenshots')  
          
        # Scroll and capture screenshots  
        scroll_position = 0  
        screenshot_index = 0  
        while scroll_position < total_height:  
            driver.execute_script(f"window.scrollTo(0, {scroll_position})")  
            time.sleep(1)  # Pause to let the page render  
            screenshot_path = f'screenshots/screenshot_{screenshot_index}.png'  
            driver.save_screenshot(screenshot_path)  
            print(f"Saved screenshot: {screenshot_path}")  
            scroll_position += viewport_height  
            screenshot_index += 1  
          
        # Optionally, stitch screenshots together  
        stitch_screenshots('screenshots', output_path)  
    finally:  
        driver.close()  
  
def stitch_screenshots(screenshot_folder, output_path):  
    screenshots = [Image.open(os.path.join(screenshot_folder, f)) for f in sorted(os.listdir(screenshot_folder))]  
    total_width = screenshots[0].width  
    total_height = sum(img.height for img in screenshots)  
      
    stitched_image = Image.new('RGB', (total_width, total_height))  
    y_offset = 0  
    for img in screenshots:  
        stitched_image.paste(img, (0, y_offset))  
        y_offset += img.height  
    stitched_image.save(output_path)  
    print(f"Stitched image saved as: {output_path}")  

# Function to get embeddings  
  
def get_embedding(text: str, model_name: str = "gpt-3.5-turbo"):  
    # Replace newlines with spaces  
    text = text.replace("\n", " ")  
      
    # Initialize the tokenizer for the model  
    tokenizer = tiktoken.encoding_for_model(model_name)  
      
    # Encode the text into tokens  
    tokens = tokenizer.encode(text)  
      
    # Truncate tokens to ensure they're under 8100 tokens  
    max_tokens = 8100  
    if len(tokens) > max_tokens:  
        tokens = tokens[:max_tokens]  
      
    # Decode tokens back to text  
    truncated_text = tokenizer.decode(tokens)  
      
    return openai_client.embeddings.create(input=[truncated_text], model=openai_emb_engine).data[0].embedding  


def ingest_data_to_cosmos(input_file_path):  
    # Read data from JSONL file  
    with open(input_file_path, 'r', encoding='utf-8') as file:  
        for line in file:  
            # Parse JSONL line  
            record = json.loads(line)  
              
            # Get embeddings for title and content  
            title_vector = get_embedding(record['title'])  
            content_vector = get_embedding(record['content'])  
              
            # Generate a UUID for the document ID  
            document_id = str(uuid.uuid4())  
              
            # Prepare the document for CosmosDB  
            document = {  
                "id": document_id,  # Use generated UUID as the document ID  
                "url": record['url'],  # Add the URL  
                "topic_vector": title_vector,  # Store title vector as 'topic_vector'  
                "content_vector": content_vector,  # Store content vector as 'content_vector'  
                "title": record['title'],  # Add the title as 'topic'  
                "content": record['content'],  # Add the content  
                "product": record['product'],  # Add default value for 'product'  
                "source": record['source'],  # Add default value for 'source'
                "timestamp": record['timestamp']  # Add the timestamp
            }  
              
            # Insert the document into CosmosDB  
            cosmos_container_client.upsert_item(document)  
  
    print("Data processing and insertion completed.")  