import asyncio
import yaml
import os

from data_ingestion.ingest_intercom import ingest_intercom
from data_ingestion.ingest_notion import ingest_notion
from data_ingestion.utils import ingest_data_to_cosmos


def load_product_mapping(file_path: str):
    with open(file_path, 'r') as file:
        product_mapping = yaml.safe_load(file)
    return product_mapping['products']


async def ingest_product_documentation(ingestion_source="all"):
    product_mapping_path = 'data_ingestion/product_mapping.yaml'
    output_file = 'processed_data/extracted_data.jsonl'

    # Load product mapping  
    products = load_product_mapping(product_mapping_path)

    # Make sure the output directory exists  
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Process each product  
    for product in products:
        product_name = product['product_name']
        data_sources = product['data_source']
        root_pages = product['root_pages']
        intercom_secret_key = product.get('intercom_secret_key', None)

        # Check if there are multiple data sources (e.g., for "Transport Operations")  
        if isinstance(data_sources, list):
            for source in data_sources:
                root_collection_ids = root_pages.get(source, [])
                if source == 'notion' and root_collection_ids and (
                        ingestion_source == "notion" or ingestion_source == "all"):
                    await ingest_notion(product_name, root_collection_ids, source='notion', output_file=output_file)
                elif source == 'intercom' and root_collection_ids and (
                        ingestion_source == "intercom" or ingestion_source == "all"):
                    await ingest_intercom(product_name, root_collection_ids, source='intercom', output_file=output_file,
                                          secret_key=intercom_secret_key)
        else:
            if data_sources == 'notion' and root_pages and (ingestion_source == "notion" or ingestion_source == "all"):
                await ingest_notion(product_name, root_pages, source='notion', output_file=output_file)
            elif data_sources == 'intercom' and root_pages and (
                    ingestion_source == "intercom" or ingestion_source == "all"):
                await ingest_intercom(product_name, root_pages, source='intercom', output_file=output_file,
                                      secret_key=intercom_secret_key)

    # Ingest data into CosmosDB
    ingest_data_to_cosmos(output_file)


if __name__ == "__main__":
    asyncio.run(ingest_product_documentation())
