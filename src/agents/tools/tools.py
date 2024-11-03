import os  
from azure.cosmos import CosmosClient  
from azure.identity import DefaultAzureCredential  
from openai import AzureOpenAI  
from dotenv import load_dotenv  
from requests_html import HTMLSession  

import re
import time  
class Tool:  
    def __init__(self):  
        load_dotenv()  
          
        # Retrieve environment variables for AAD authentication  
        aad_client_id = os.getenv("AAD_CLIENT_ID")  
        aad_client_secret = os.getenv("AAD_CLIENT_SECRET")  
        aad_tenant_id = os.getenv("AAD_TENANT_ID")  
  
        # Configure CosmosDB client with AAD authentication  
        cosmos_uri = os.environ.get("COSMOS_URI")  
        container_name = os.getenv("COSMOS_CONTAINER_NAME")  
        cosmos_db_name = os.getenv("COSMOS_DB_NAME")  
  
        # Set up the DefaultAzureCredential with the client ID, client secret, and tenant ID  
        os.environ["AZURE_CLIENT_ID"] = aad_client_id  
        os.environ["AZURE_CLIENT_SECRET"] = aad_client_secret  
        os.environ["AZURE_TENANT_ID"] = aad_tenant_id  
  
        # Use DefaultAzureCredential for authentication  
        credential = DefaultAzureCredential()  
        self.client = CosmosClient(cosmos_uri, credential=credential)  
        self.cosmos_db_client = self.client.get_database_client(cosmos_db_name)  
        self.cosmos_container_client = self.cosmos_db_client.get_container_client(container_name)  
  
        self.openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
        self.openai_client = AzureOpenAI(  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  
        )  
        self.openai_chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
        self.openai_processing_engine = os.getenv("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT")  

    def search_knowledge_base(self, question: str, product: str, topk: int = 3) -> str:  
        """Search the knowledge base using CosmosDB and return top-k results."""  
        print("question", question)  
        query_embedding = self._get_embedding(question)  
  
        # Query the database for the most similar items based on content vector and filter by product  
        results = self.cosmos_container_client.query_items(  
            query=(  
                'SELECT TOP @topk c.url, c.topic, c.content, '  
                'VectorDistance(c.topic_vector, @embedding) AS Topic_SimilarityScore, '  
                'VectorDistance(c.content_vector, @embedding) AS Content_SimilarityScore '  
                'FROM c WHERE c.product = @product '  
                'ORDER BY VectorDistance(c.content_vector, @embedding)'  
            ),  
            parameters=[  
                {"name": "@embedding", "value": query_embedding},  
                {"name": "@product", "value": product},  
                {"name": "@topk", "value": topk}  
            ],  
            enable_cross_partition_query=True  
        )  
  
        # Collect the results into a formatted string  
        text_content = "\n".join(f"{result['url']}\n{result['topic']}\n{result['content']}" for result in results)  
        return text_content  
  
    def _get_embedding(self, text: str) -> list:  
        text = text.replace("\n", " ")  
        return self.openai_client.embeddings.create(input=[text], model=self.openai_emb_engine).data[0].embedding  

    def get_help(self, user_request: str) -> str:  
        return f"{user_request}"  
    def get_content_from_url(self, url: str, method: str = "web") -> str:  
        """  
        Retrieve content from a given URL using the specified method.  
  
        :param url: The URL to retrieve content from.  
        :param method: The method to use for retrieval - either 'cosmosdb' or 'web'.  
        :return: The retrieved content as a string.  
        """  
        if method == "cosmosdb":  
            return self._get_content_from_cosmosdb(url)  
        else:  
            return self._get_content_from_web(url)  
  
    def _get_content_from_cosmosdb(self, url: str) -> str:  
        """  
        Retrieve content from CosmosDB using the URL as the filter parameter.  
  
        :param url: The URL to filter by.  
        :return: The content as a string.  
        """  
        # Query the CosmosDB using the URL as a filter  
        results = self.cosmos_container_client.query_items(  
            query='SELECT c.content FROM c WHERE c.url = @url',  
            parameters=[{"name": "@url", "value": url}],  
            enable_cross_partition_query=True  
        )  
  
        # Collect and return the content from the query results  
        content = "\n".join(result['content'] for result in results)  
        return content  

    def _get_content_from_web(self, url: str) -> str:  
        """  
        Retrieve content from the web for the given URL, including descriptions for images.  
  
        :param url: The URL to retrieve content from.  
        :return: The extracted content as a string.  
        """  
        # Initialize HTML session  
        session = HTMLSession()  
  
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
  
                response = self.openai_client.chat.completions.create(  
                    model=self.openai_chat_engine,  
                    messages=messages,  
                )  
  
                extracted_content = response.choices[0].message.content.strip()  
                return extracted_content  
  
            except Exception as e:  
                print(f"Failed to extract content from {url}: {e}")  
                time.sleep(5)  # Sleep and try again after 5 seconds  
                return extract_content_from_url(url, retries + 1)  # Retry with incremented retry count  
  
        def get_image_description(image_url, retries=0):  
            max_retries = 2
            try:  
                response = self.openai_client.chat.completions.create(  
                    model=self.openai_processing_engine,  
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
        def replace_image_urls_with_descriptions(extracted_content):  
            image_urls = re.findall(r'\!\[.*?\]\((https?://.*?\.(?:png|jpg|jpeg|gif)(?:\?.*?)?)\)', extracted_content)  
            for image_url in image_urls:  
                description = get_image_description(image_url)  
                extracted_content = extracted_content.replace(image_url, description)  
            return extracted_content  
  
        # Extract and process content from the main URL  
        extracted_content = extract_content_from_url(url)  
        if extracted_content is None:  
            return "Failed to retrieve content from the web."  
  
        # Replace image URLs with descriptions  
        content_with_image_descriptions = replace_image_urls_with_descriptions(extracted_content)  
  
        return content_with_image_descriptions  
