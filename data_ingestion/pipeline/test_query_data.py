import os  
import json  
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
  
# Function to get embeddings  
openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
openai_chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
openai_client = AzureOpenAI(  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  
)  

def get_embedding(text: str):  
    text = text.replace("\n", " ")  
    return openai_client.embeddings.create(input=[text], model=openai_emb_engine).data[0].embedding  
  
# Input query  
query_text = "how to monitor your supply chain in real time"  
  
# Get embedding for the query  
query_embedding = get_embedding(query_text)  
  
# Query the database for the most similar items based on title vector  
results = cosmos_container_client.query_items(  
    query='SELECT TOP 3 c.url, c.topic, c.content, VectorDistance(c.topic_vector, @embedding) AS Topic_SimilarityScore,VectorDistance(c.content_vector, @embedding) AS Content_SimilarityScore FROM c ORDER BY VectorDistance(c.content_vector, @embedding)' ,  
    parameters=[  
        {"name": "@embedding", "value": query_embedding}  
    ],  
    enable_cross_partition_query=True  
)  
for result in results:
    print(result)

