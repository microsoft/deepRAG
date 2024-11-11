from dotenv import load_dotenv  
from openai import AzureOpenAI  
import time  
import os  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
  
import time
  
# Load environment variables  
load_dotenv()  
  
  
# Initialize Azure OpenAI client  
processing_engine = os.getenv("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT")  
openai_client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version="2024-10-01-preview",  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  


batch_input_file = openai_client.files.create(
  file=open("data_ingestion/batch_openai.jsonl", "rb"),
  purpose="batch"
)

batch_input_file_id = batch_input_file.id
time.sleep(5)
# Submit a batch job with the file
batch_response = openai_client.batches.create(
    input_file_id=batch_input_file_id,
    endpoint="/chat/completions",
    completion_window="24h",
)

# Save batch ID for later use
batch_id = batch_response.id

print(batch_response.model_dump_json(indent=2))
