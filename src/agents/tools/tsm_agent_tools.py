from .tools import Tool  

class TsmAgentTool(Tool):  
    def __init__(self):  
        super().__init__()  
  
    def search_knowledgebase(self, search_query: str) -> str:  
        return self.search_knowledge_base(search_query, product='control_center', topk=3)  