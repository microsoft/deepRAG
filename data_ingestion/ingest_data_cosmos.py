import json  
import os  
import uuid  
from azure.cosmos import CosmosClient  
from azure.identity import DefaultAzureCredential  
from dotenv import load_dotenv  
from openai import AzureOpenAI
# Load environment variables  
load_dotenv()  
  
# Retrieve environment variables for AAD authentication  
aad_client_id = os.getenv("AAD_CLIENT_ID")  
aad_client_secret = os.getenv("AAD_CLIENT_SECRET")  
aad_tenant_id = os.getenv("AAD_TENANT_ID")  
  
# Configure CosmosDB client with AAD authentication  
cosmos_uri = os.environ.get("COSMOS_URI")  
container_name = os.getenv("COSMOS_CONTAINER_NAME")  
cosmos_db_name = os.getenv("COSMOS_DB_NAME")  
openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
  
# Set up the DefaultAzureCredential with the client ID, client secret, and tenant ID  
os.environ["AZURE_CLIENT_ID"] = aad_client_id  
os.environ["AZURE_CLIENT_SECRET"] = aad_client_secret  
os.environ["AZURE_TENANT_ID"] = aad_tenant_id  
  
# Use DefaultAzureCredential for authentication  
credential = DefaultAzureCredential()  
client = CosmosClient(cosmos_uri, credential=credential)  
cosmos_db_client = client.get_database_client(cosmos_db_name)  
cosmos_container_client = cosmos_db_client.get_container_client(container_name)  
openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
openai_chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
openai_client = AzureOpenAI(  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  
)  

# Function to get embeddings  
def get_embedding(text: str):  
    text = text.replace("\n", " ")  
    return openai_client.embeddings.create(input=[text], model=openai_emb_engine).data[0].embedding  
  
# Read data from JSONL file  
input_file_path = "processed_data/extracted_content.jsonl"  
  
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
            "topic": record['title'],  # Add the title as 'topic'  
            "content": record['content'],  # Add the content  
            "product": "control_center"  # Add default value for 'product'  
        }  
          
        # Insert the document into CosmosDB  
        cosmos_container_client.upsert_item(document)  
  
print("Data processing and insertion completed.")  