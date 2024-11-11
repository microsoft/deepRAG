import json
import uuid  
from azure.cosmos import CosmosClient
from openai import AzureOpenAI

# Function to get embeddings  
def get_embedding(openai_client:AzureOpenAI, openai_emb_engine: str, text: str):  
    text = text.replace("\n", " ")  
    return openai_client.embeddings.create(input=[text], model=openai_emb_engine).data[0].embedding  
  
def store_documents(openai_client:AzureOpenAI, client: CosmosClient, cosmos_db_name:str, container_name: str, openai_emb_engine: str, processed_data):  
    cosmos_db_client = client.get_database_client(cosmos_db_name)  
    cosmos_container_client = cosmos_db_client.get_container_client(container_name)  

    for record in processed_data:
            
        # Get embeddings for title and content  
        title_vector = get_embedding(openai_client, openai_emb_engine, record['title'])  
        content_vector = get_embedding(openai_client, openai_emb_engine, record['content'])  
            
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