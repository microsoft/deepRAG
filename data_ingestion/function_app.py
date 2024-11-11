import os
import azure.functions as func
import logging

from openai import AzureOpenAI  
from azure.cosmos import CosmosClient  
from azure.identity import DefaultAzureCredential  
from requests_html import HTMLSession  
from pipeline.web_crawling_agent import process_urls_and_write_to_file
from pipeline.ingest_data_cosmos import store_documents

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Initialize HTML session  
    session = HTMLSession()  
    
    # Initialize Azure OpenAI client  
    engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
    processing_engine = os.getenv("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT")
    openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
    cosmos_uri = os.environ.get("COSMOS_URI")  
    container_name = os.getenv("COSMOS_CONTAINER_NAME")  
    cosmos_db_name = os.getenv("COSMOS_DB_NAME")  
    credential = DefaultAzureCredential()  
    cosmosClient = CosmosClient(cosmos_uri, credential=credential)  
    client = AzureOpenAI(  
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
    )

    embedding_client = AzureOpenAI(  
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
    )

    # URL of the main article  
    main_article_url = 'https://intercom.help/sixfold/en/articles/6023034-visibility-control-center-for-shippers-lsps'  
    # Output file name  
    output_file_name = 'processed_data/extracted_content.jsonl'  

    # Execute the main process with a depth limit of 10  
    DEPTH_LIMIT = 10
    MAX_ENTRIES = 20
    
    processed_data = process_urls_and_write_to_file(
        client,
        processing_engine,
        engine,
        session,
        main_article_url,
        output_file_name,
        depth_limit=DEPTH_LIMIT,
        max_entries=MAX_ENTRIES
    )

    store_documents(embedding_client, cosmosClient, cosmos_db_name, container_name, openai_emb_engine, processed_data)
    
    return func.HttpResponse(f"Done.")