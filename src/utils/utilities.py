# Agent class
# responsbility definition: expertise, scope, conversation script, style
from pathlib import Path
import json
import os
import base64
from openai import AzureOpenAI
import streamlit as st
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
env_path = Path('..') / '.env'
load_dotenv(dotenv_path=env_path)
MAX_ERROR_RUN = 3
MAX_RUN_PER_QUESTION = 10
MAX_QUESTION_TO_KEEP = 3
MAX_QUESTION_WITH_DETAIL_HIST = 1

env: os._Environ[str] = os.environ
getenv = os.getenv
emb_engine = getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
chat_engine = getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
client = AzureOpenAI(
    api_key=env.get("AZURE_OPENAI_API_KEY"),
    api_version=getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=env.get("AZURE_OPENAI_ENDPOINT"),
)
max_conversation_len = 5  # Set the desired value of k


emb_engine: str | None = getenv("AZURE_OPENAI_EMB_DEPLOYMENT")
# azcs implementation
searchservice: str | None = getenv("AZURE_SEARCH_ENDPOINT")
index_name: str | None = getenv("AZURE_SEARCH_INDEX_NAME")
key: str | None = getenv("AZURE_SEARCH_KEY")
search_client = SearchClient(
    endpoint=searchservice,
    index_name=index_name,
    credential=AzureKeyCredential(key=getenv("AZURE_SEARCH_KEY"))
)


# @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
# Function to generate embeddings for title and content fields, also used for query embeddings
def get_embedding(text, model=emb_engine):
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding


credential = AzureKeyCredential(key)


def get_text_embedding(text, model=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")):
    text = text.replace("\n", " ")
    while True:
        try:
            embedding_response = client.embeddings.create(
                input=[text], model=model).data[0].embedding
            return embedding_response
        except openai.error.RateLimitError:
            print("Rate limit exceeded. Retrying after 10 seconds...")
            time.sleep(10)


today = pd.Timestamp.today()
# format today's date
today = today.strftime("%Y-%m-%d")
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


def search(search_query):
    print("search query: ", search_query)
    vector_query = VectorizedQuery(vector=get_text_embedding(
        search_query), k_nearest_neighbors=3, fields="contentVector")

    results = search_client.search(

        query_type=QueryType.SEMANTIC, semantic_configuration_name='my-semantic-config', query_caption=QueryCaptionType.EXTRACTIVE, query_answer=QueryAnswerType.EXTRACTIVE,

        vector_queries=[vector_query],
        select=["topic", "file_name", "page_number", "related_content"],
        top=3
    )
    images_directory = ".\\processed_data"
    output = []
    for result in results:
        print(f"topic: {result['topic']}")
        print("related_content: ", result['related_content'])

        page_image = os.path.join(
            images_directory, result['file_name'], "page_" + str(result['page_number']))+".png"
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


def check_args(function, args):
    sig = inspect.signature(function)
    params = sig.parameters

    # Check if there are extra arguments
    for name in args:
        if name not in params:
            return False
    # Check if the required arguments are provided
    for name, param in params.items():
        if param.default is param.empty and name not in args:
            return False


def clean_up_history(history, max_q_with_detail_hist=1, max_q_to_keep=2):
    # start from end of history, count the messages with role user, if the count is more than max_q_with_detail_hist, remove messages from there with roles tool.
    # if the count is more than max_q_hist_to_keep, remove all messages from there until message number 1
    question_count = 0
    removal_indices = []
    for idx in range(len(history)-1, 0, -1):
        message = dict(history[idx])
        if message.get("role") == "user":
            question_count += 1
            # print("question_count added, it becomes: ", question_count)
        if question_count >= max_q_with_detail_hist and question_count < max_q_to_keep:
            if message.get("role") != "user" and message.get("role") != "assistant" and len(message.get("content")) == 0:
                removal_indices.append(idx)
        if question_count >= max_q_to_keep:
            removal_indices.append(idx)

    # remove items with indices in removal_indices
    for index in removal_indices:
        del history[index]


def reset_history_to_last_question(history):
    # pop messages from history from last item to the message with role user
    for i in range(len(history)-1, -1, -1):
        message = dict(history[i])
        if message.get("role") == "user":
            break
        history.pop()
    for session_item in st.session_state:
        if 'data_from_display' in session_item or 'comment_on_graph' in session_item:
            del st.session_state[session_item]


class Smart_Agent():
    """
    """

    def __init__(self, persona, functions_spec, functions_list, name=None, init_message=None, engine=chat_engine):
        if init_message is not None:
            init_hist = [{"role": "system", "content": persona},
                         {"role": "assistant", "content": init_message}]
        else:
            init_hist = [{"role": "system", "content": persona}]

        self.conversation = init_hist
        self.persona = persona
        self.engine = engine
        self.name = name

        self.functions_spec = functions_spec
        self.functions_list = functions_list
    # @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))

    def run(self, user_input, conversation=None, stream=False, ):
        if user_input is None:  # if no input return init message
            return self.conversation, self.conversation[1]["content"]
        if conversation is not None:  # if no history return init message
            self.conversation = conversation

        self.conversation.append(
            {"role": "user", "content": user_input, "name": "James"})
        clean_up_history(self.conversation, max_q_with_detail_hist=MAX_QUESTION_WITH_DETAIL_HIST,
                         max_q_to_keep=MAX_QUESTION_TO_KEEP)

        execution_error_count = 0
        code = ""
        response_message = None
        data = {}
        execution_context = {}
        run_count = 0
        while True:
            if run_count >= MAX_RUN_PER_QUESTION:
                reset_history_to_last_question(self.conversation)
                print(
                    f"Need to move on from this question due to max run count reached ({run_count} runs)")
                response_message = {
                    "role": "assistant", "content": "I am unable to answer this question at the moment, please ask another question."}
                break
            if execution_error_count >= MAX_ERROR_RUN:
                reset_history_to_last_question(self.conversation)
                print(
                    f"resetting history due to too many errors ({execution_error_count} errors) in the code execution")
                execution_error_count = 0
            response = client.chat.completions.create(
                # The deployment name you chose when you deployed the GPT-35-turbo or GPT-4 model.
                model=self.engine,
                messages=self.conversation,
                tools=self.functions_spec,

                tool_choice='auto',
                temperature=0.2,


            )
            run_count += 1
            response_message = response.choices[0].message
            if response_message.content is None:
                response_message.content = ""
            tool_calls = response_message.tool_calls

            if tool_calls:
                # print("Tool calls: ")
                # extend conversation with assistant's reply
                self.conversation.append(response_message)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name

                    print("Recommended Function call:")
                    print(function_name)
                    print()

                    # verify function exists
                    if function_name not in self.functions_list:
                        # raise Exception("Function " + function_name + " does not exist")
                        print(("Function " + function_name +
                              " does not exist, retrying"))
                        self.conversation.pop()
                        break
                    function_to_call = self.functions_list[function_name]

                    # verify function has correct number of arguments
                    try:
                        function_args = json.loads(
                            tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        print(e)
                        self.conversation.pop()
                        break
                    if check_args(function_to_call, function_args) is False:
                        self.conversation.pop()
                        break

                    else:
                        function_response = function_to_call(**function_args)

                    if function_name == "search":
                        search_function_response = []
                        for item in function_response:
                            image_path = item['image_path']
                            related_content = item['related_content']

                            with open(image_path, "rb") as image_file:
                                base64_image = base64.b64encode(
                                    image_file.read()).decode('utf-8')
                            # path= "_".join(image_path.split("\\")[-2:])
                            print("image_path: ", image_path)

                            search_function_response.append(
                                {"type": "text", "text": f"file_name: {image_path}"})
                            search_function_response.append({"type": "image_url", "image_url": {
                                                            "url":  f"data:image/jpeg;base64,{base64_image}"}})
                            search_function_response.append(
                                {"type": "text", "text": f"HINT: The following kind of content might be related to this topic\n: {related_content}"})

                        function_response = search_function_response
                    self.conversation.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )  # extend conversation with function response

                continue
            else:
                # print('no function call')
                break  # if no function call break out of loop as this indicates that the agent finished the research and is ready to respond to the user

        if not stream:
            self.conversation.append(response_message)
            if type(response_message) is dict:
                assistant_response = response_message.get('content')
            else:
                assistant_response = response_message.dict().get('content')
            # conversation.append({"role": "assistant", "content": assistant_response})

        else:
            assistant_response = response_message

        return stream, code, self.conversation, assistant_response, data
