# Agent class
# responsbility definition: expertise, scope, conversation script, style
from pathlib import Path
import os
from typing import List, Literal
from openai import AzureOpenAI
from settings import Settings
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import time
from azure.search.documents.models import (

    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizedQuery,
)

import pandas as pd
from dotenv import load_dotenv
import inspect
import openai
env_path: Path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)
settings: Settings = Settings(__env_path=env_path) # type: ignore

MAX_ERROR_RUN = 3
MAX_RUN_PER_QUESTION = 10
MAX_QUESTION_TO_KEEP = 3
MAX_QUESTION_WITH_DETAIL_HIST = 1

emb_engine: str = settings.openai_embedding_deployment
chat_engine: str = settings.openai_chat_deployment
client = AzureOpenAI(
    api_key=settings.openai_key,
    api_version=settings.openai_api_version,
    azure_endpoint=settings.openai_endpoint,
)
max_conversation_len = 5  # Set the desired value of k
searchservice: str = settings.azure_search_endpoint
index_name: str = settings.azure_search_index_name
key: str = settings.azure_search_key
credential = AzureKeyCredential(key=key)
search_client = SearchClient(
    endpoint=searchservice,
    index_name=index_name,
    credential=credential
)

# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def get_embedding(text, model=emb_engine):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding

def get_text_embedding(text, model=emb_engine) -> List[float]:
    text = text.replace("\n", " ")
    while True:
        try:
            return client.embeddings.create(
                input=[text], model=model).data[0].embedding
        except openai.RateLimitError:
            print("Rate limit exceeded. Retrying after 10 seconds...")
            time.sleep(10)


today: str = pd.Timestamp.today().strftime(format="%Y-%m-%d")
PERSONA = """
You are an intelligent AI assistant designed to help users find information most relevant to their questions. 
You have access to Azure AI Search, which provides semantic search capabilities using natural language queries and metadata filtering. 
The data you access is organized according to the ontology below.
As a smart research assistant, your goal is to identify the best relevant information to answer the user's question. 
The initial search result may include hints on the related content. Use hint to start a follow-up search to find related content if neccessary.
Engage with the user to understand their needs, conduct the research, and respond with a curated list of content along with explanations on how they can be used to answer the user's question.
Your final response should be in JSON format like this:
{
  "overall_explanation": "The following headlines are inspired by the concept of customization and personal expression, which resonates well with young people. These suggestions are derived from the context of launching a product that allows users to make it their own.",
  "11_LAUNCHING_MAKE_YOUR_WORLD_2022-11-17/page_7.png": "This file provides a context for launching a product with a focus on personalization and making it your own.",
  "Brand_Context/page_18.png": "This file offers insights into brand context and how to position a product in a way that appeals to young people by emphasizing individuality and customization."
}
Just output the JSON content in your final response and do not add any other comment.

# Ontology   
EntityClasses:  
  - Brand:  
      Description: "An entity representing a company's identity, values, and image."  
      Attributes:  
        - Name: "The official name of the brand."  
        - TargetConsumer: "The primary demographic the brand aims to reach."  
        - Slogan: "A memorable phrase representing the brand's essence."  
        - ColorPalette: "The set of colors used for brand identity."  
        - LogoUsage: "Guidelines for using the brand's logo."  
        - StoryboardGuidelines: "Rules for visual storytelling."  
        - SocialMediaGuidelines: "Instructions for maintaining brand consistency on social media."  
  
  - Product:  
      Description: "An item or service offered by the brand."  
      Attributes:  
        - Name: "The official name of the product."  
        - Type: "The category of the product, e.g., SaaS, On-Premise."  
        - Popularity: "The level of market acceptance and usage."  
        - Market: "The primary geographic or demographic market for the product."  
  
  - Campaign:  
      Description: "A series of coordinated activities aimed at promoting a product or brand."  
      Attributes:  
        - Name: "The official name of the campaign."  
        - Focus: "The main theme or objective, e.g., Digital Experience, AI."  
        - Market: "The target market for the campaign."  
        - CreativeAssets: "Visual and textual materials used in the campaign."  
        - Concept: "The central idea or message of the campaign."  
        - Toolkit: "Resources and tools used to execute the campaign."  
  
  - Guideline:  
      Description: "A set of rules or instructions for maintaining brand consistency."  
      Attributes:  
        - Type: "The category of the guideline, e.g., Digital Asset, Tone of Voice Usage, Logo Usage."  
        - Details: "Specific instructions and details."  
  
  - Market:  
      Description: "A defined geographic or demographic area where products are sold."  
      Attributes:  
        - Name: "The name of the market."  
        - Trends: "Current market trends and dynamics."  
        - Competitors: "Main competitors within the market."  
        - Influencers: "Key influencers relevant to the market."  
  
  - Competitor:  
      Description: "A company or product competing with the brand."  
      Attributes:  
        - Name: "The name of the competitor."  
        - Products: "Products offered by the competitor."  
        - Campaigns: "Promotional campaigns run by the competitor."  
  
  - Influencer:  
      Description: "A person who can influence the brand's target audience."  
      Attributes:  
        - Name: "The name of the influencer."  
        - Market: "The market segment the influencer operates in."  
        - Segment: "Specific niche or category, e.g., Coffee, Lifestyle."  
  
  - AdvertisingCase:  
      Description: "A documented instance of brand advertising."  
      Attributes:  
        - Market: "The market where the advertising case is relevant."  
        - Details: "Specific details about the advertising case."  
  
  - Aesthetic:  
      Description: "The visual style and design elements used by the brand."  
      Attributes:  
        - Style: "The design style, e.g., Minimalist, Modern."  
        - TargetAudience: "The audience for whom the aesthetic is designed."  
  
  - Recipe:  
      Description: "A detailed set of instructions for creating a product."  
      Attributes:  
        - Name: "The name of the recipe."  
        - Ingredients: "The components required for the recipe."  
        - Steps: "The sequence of actions to complete the recipe."  
  
  - Claim:  
      Description: "A statement made by the brand to promote its values or product benefits."  
      Attributes:  
        - Type: "The category of claim, e.g., Sustainability, Quality, Safety."  
        - Details: "Specific details of the claim."  
  
  - Slogan:  
      Description: "A memorable phrase used in marketing to represent the brand's essence."  
      Attributes:  
        - Text: "The actual slogan text."  
        - Language: "The language in which the slogan is written."  
        - UsageContext: "The context or situation in which the slogan is used."  
  
Relationships:  
  - Brand:  
      - has_product: Product  
      - runs_campaign: Campaign  
      - follows_guideline: Guideline  
      - targets_market: Market  
      - competes_with: Competitor  
      - collaborates_with: Influencer  
      - featured_in_advertising_case: AdvertisingCase  
      - makes_claim: Claim  
      - uses_slogan: Slogan  
  
  - Product:  
      - belongs_to_brand: Brand  
      - popular_in_market: Market  
      - competes_with: Competitor  
      - follows_guideline: Guideline  
      - includes_recipe: Recipe  
  
  - Campaign:  
      - belongs_to_brand: Brand  
      - targets_market: Market  
      - uses_guideline: Guideline  
      - includes_toolkit: Toolkit  
  
  - Guideline:  
      - applies_to_brand: Brand  
      - applies_to_product: Product  
      - applies_to_campaign: Campaign  
  
  - Market:  
      - includes_product: Product  
      - includes_competitor: Competitor  
      - includes_influencer: Influencer  
  
  - Competitor:  
      - competes_with_brand: Brand  
      - competes_with_product: Product  
  
  - Influencer:  
      - collaborates_with_brand: Brand  
  
  - AdvertisingCase:  
      - features_brand: Brand  
  
  - Recipe:  
      - belongs_to_product: Product  
      - follows_aesthetic: Aesthetic  
  
  - Claim:  
      - made_by_brand: Brand  
  
  - Slogan:  
      - used_by_brand: Brand  
"""

def search(search_query, settings: Settings):
    print("search query: ", search_query)
    vector_query = VectorizedQuery(
        vector=get_text_embedding(text=search_query),
        k_nearest_neighbors=3,
        fields="contentVector")

    results = search_client.search(
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name='my-semantic-config',
        query_caption=QueryCaptionType.EXTRACTIVE,
        query_answer=QueryAnswerType.EXTRACTIVE,
        vector_queries=[vector_query],
        select=["topic", "file_name", "page_number", "related_content"],
        top=3
    )
    images_directory: str = settings.smart_agent_image_path
    output = []
    for result in results:
        print(f"topic: {result['topic']}")
        print("related_content: ", result['related_content'])
        page_image = Path(images_directory, os.path.join(
            images_directory,
            result['file_name'],
            f"page_{str(object=result['page_number'])}.png"))
        output.append({'image_path': page_image,
                      'related_content': result['related_content']})
    return output


AVAILABLE_FUNCTIONS = {
    "search": search,
}

FUNCTIONS_SPEC = [

    {
        "type": "function",
        "function": {

            "name": "search",
            "description": "Semantic Search Engine to search for content",

            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "Natural language query to search for content"
                    }


                },
                "required": ["search_query"],
            },
        }
    },
]

def check_args(function, args) -> None | Literal[False]:
    sig: inspect.Signature = inspect.signature(obj=function)
    params = sig.parameters

    # Check if there are extra arguments
    for name in args:
        if name not in params:
            return False
    # Check if the required arguments are provided
    for name, param in params.items():
        if param.default is param.empty and name not in args:
            return False
