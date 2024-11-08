import json  
import os  
import uuid  
import fitz  # PyMuPDF  
from PIL import Image  
import time  
import base64  
from multiprocessing import Pool, cpu_count  
from azure.cosmos import CosmosClient  
from azure.identity import DefaultAzureCredential  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from concurrent.futures import ThreadPoolExecutor, as_completed  
def encode_image(image_path):  
    with open(image_path, "rb") as image_file:  
        return base64.b64encode(image_file.read()).decode('utf-8')  
  
def get_gpt_response(image_path, max_tokens=1000):  
    prompt = """
    Objective: Extract content from this image and convert it into raw markdown format.  
Instructions:  
1. Text:  
    - Retain the original formatting of the text as seen in the image.  
    - Pay attention to elements such as headings, paragraphs, lists, and emphasis (bold or italic text).  
2. Tabular Data:  
    - Convert any tables into markdown tables using the appropriate markdown tags.  
    - Ensure that the structure of rows and columns is preserved accurately.  
3. Graphs and Images:  
    - Provide a detailed description of any graphs or images.  
    - Include information about axes, labels, legends, and notable trends or features.  
Output Requirements:  
    - The final markdown output should closely resemble the layout and organization of the original content in the image.  
    - Ensure that all elements (text, tables, images) are clearly and correctly represented in markdown format.
    - Do not add any commments, just output the markdown content.  
    """  
      
    message_content = [{"type": "text", "text": prompt}]  
      
    base64_image = encode_image(image_path)  
    message_content.append({  
        "type": "image_url",  
        "detail": "low",  
        "image_url": {  
            "url": f"data:image/jpeg;base64,{base64_image}",  
        },  
    })  
      
    response = client.chat.completions.create(  
        model=os.environ.get("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT"),  
        messages=[  
            {  
                "role": "user",  
                "content": message_content,  
            }  
        ],  
        max_tokens=max_tokens,  
    )  
      
    return response.choices[0].message.content  
  
def process_image(image_path):  
    return get_gpt_response(image_path)  
  
def process_page_block(args):  
    pdf_path, pdf_output_folder, start_page, end_page = args  
    pdf_document = fitz.open(pdf_path)  
      
    for page_num in range(start_page, end_page):  
        page = pdf_document.load_page(page_num)  
        pix = page.get_pixmap()  
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  
        img_filename = f'page_{page_num + 1}.png'  
        img_path = os.path.join(pdf_output_folder, img_filename)  
        img.save(img_path)  
      
    pdf_document.close()  
  
def process_pdf(pdf_file, block_size):  
    pdf_file_underscored = pdf_file.replace(' ', '_')  
    pdf_path = os.path.join(input_folder, pdf_file)  
    pdf_document = fitz.open(pdf_path)  
    pdf_name = os.path.splitext(pdf_file_underscored)[0]  
    pdf_output_folder = os.path.join(output_folder, pdf_name)  
    os.makedirs(pdf_output_folder, exist_ok=True)  
      
    num_pages = len(pdf_document)  
    pdf_document.close()  
    page_blocks = [(pdf_path, pdf_output_folder, start, min(start + block_size, num_pages))  
                   for start in range(0, num_pages, block_size)]  
  
    # Process each block of pages  
    for block in page_blocks:  
        process_page_block(block)  
  
    # Collect images for processing  
    image_paths = [os.path.join(pdf_output_folder, filename)   
                   for filename in os.listdir(pdf_output_folder) if filename.endswith(".png")]  
  
    # Define the maximum number of concurrent threads  
    max_concurrent_calls = 120  # You can set this to your desired number  
    
    # Process images with ThreadPoolExecutor  
    with ThreadPoolExecutor(max_workers=max_concurrent_calls) as executor:  
        # Submit tasks to the executor  
        future_to_image = {executor.submit(process_image, image_path): image_path for image_path in image_paths}  
        
        # Collect results as they complete  
        results = []  
        for future in as_completed(future_to_image):  
            image_path = future_to_image[future]  
            try:  
                result = future.result()  
                results.append(result)  
            except Exception as exc:  
                print(f'Image processing generated an exception: {exc} for image {image_path}')  
    # Save results to a JSONL file  
    output_file_path = os.path.join(output_folder, f"{pdf_name}_output.jsonl")  
    with open(output_file_path, 'w', encoding='utf-8') as output_file:  
        for result in results:  
            json.dump({"markdown_content": result}, output_file)  
            output_file.write('\n')  
  
    def ingest_to_cosmosdb(results):  
        max_concurrent_calls = 20  # Set this to your desired number of concurrent threads  
    
        # Define a function to upsert a document into CosmosDB  
        def upsert_document(result):  
            content_vector = get_embedding(result)  
            document_id = str(uuid.uuid4())  
            document = {  
                "id": document_id,  
                "user_id": "user_123",  # Default user ID  
                "content_vector": content_vector,  
                "content": result  
            }  
            cosmos_container_client.upsert_item(document)  
    
        # Use ThreadPoolExecutor to parallelize the ingestion  
        with ThreadPoolExecutor(max_workers=max_concurrent_calls) as executor:  
            # Submit tasks to the executor  
            future_to_result = {executor.submit(upsert_document, result): result for result in results}  
    
            # Collect results as they complete  
            for future in as_completed(future_to_result):  
                result = future_to_result[future]  
                try:  
                    future.result()  # We don't need the result, just catching exceptions  
                except Exception as exc:  
                    print(f'CosmosDB ingestion generated an exception: {exc} for result {result}')  
    
    # Call the ingest_to_cosmosdb function with the results  
    ingest_to_cosmosdb(results)  
    print(f'Processed {pdf_file} and saved output to {output_file_path}')  
  
def get_embedding(text: str):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=openai_emb_engine).data[0].embedding  
  
if __name__ == "__main__":  
    load_dotenv()  
  
    # Azure OpenAI setup  
    client = AzureOpenAI(  
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  
    )  
  
    # CosmosDB setup  
    cosmos_uri = os.environ.get("COSMOS_URI")  
    container_name = os.getenv("COSMOS_CONTAINER_NAME_USER")  
    cosmos_db_name = os.getenv("COSMOS_DB_NAME")  
    # Retrieve environment variables for AAD authentication  
    aad_client_id = os.getenv("AAD_CLIENT_ID")  
    aad_client_secret = os.getenv("AAD_CLIENT_SECRET")  
    aad_tenant_id = os.getenv("AAD_TENANT_ID")  

    # Set up the DefaultAzureCredential with the client ID, client secret, and tenant ID  
    os.environ["AZURE_CLIENT_ID"] = aad_client_id  
    os.environ["AZURE_CLIENT_SECRET"] = aad_client_secret  
    os.environ["AZURE_TENANT_ID"] = aad_tenant_id  

    credential = DefaultAzureCredential()  
    cosmos_client = CosmosClient(cosmos_uri, credential=credential)  
    cosmos_db_client = cosmos_client.get_database_client(cosmos_db_name)  
    cosmos_container_client = cosmos_db_client.get_container_client(container_name)  
  
    openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
  
    input_folder = 'data_ingestion/input_data'  
    output_folder = 'processed_data/pdf_images'  
    os.makedirs(output_folder, exist_ok=True)  
  
    start_time = time.time()  
  
    block_size = 10  # Number of pages per block  
  
    pdf_files = [f for f in os.listdir(input_folder) if f.endswith('.pdf')]  
    for pdf_file in pdf_files:  
        process_pdf(pdf_file, block_size)  
  
    end_time = time.time()  
    print('Finished processing all PDF files in', end_time - start_time, 'seconds')  