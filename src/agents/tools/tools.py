import os  
import json  
from typing import List, Tuple  
from scipy import spatial  # for calculating vector similarities for search  
from openai import AzureOpenAI    
  
  
class Tool:  
    def __init__(self):  
        if os.getenv("EMB_MAP_FILE_PATH"):
            with open(os.getenv("EMB_MAP_FILE_PATH")) as file:  
                self.chunks_emb = json.load(file)  
  
        self.openai_emb_engine = os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT")  
        self.openai_chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
        self.openai_client = AzureOpenAI(  
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  
        )  
  
    def get_help(self, user_request: str) -> str:  
        return f"{user_request}"  
  
    def send_rich_format_message(self, message: str) -> str:  
        return f"Sending rich format message: {message}"  
  
    def search_knowledge_base(self, question: str, topk: int = 3) -> str:  
        """Search the knowledge base and return top-k results."""  
        print("question", question)  
        input_vector = self.get_embedding(question)  
        cosine_list: List[Tuple[str, str, float]] = []  
        for item in self.chunks_emb:  
            cosine_sim = 1 - spatial.distance.cosine(input_vector, item['policy_text_embedding'])  
            cosine_list.append((item['id'], item['policy_text'], cosine_sim))  
        cosine_list.sort(key=lambda x: x[2], reverse=True)  
        cosine_list = cosine_list[:topk]  
        text_content = "\n".join(f"{chunk[0]}\n{chunk[1]}" for chunk in cosine_list)  
        return text_content  
  
    def get_embedding(self, text: str) -> List[float]:  
        text = text.replace("\n", " ")  
        return self.openai_client.embeddings.create(input=[text], model=self.openai_emb_engine).data[0].embedding  