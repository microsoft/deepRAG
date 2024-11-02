import os
import redis
import pickle
import base64
from typing import Dict

class SessionState:  
    def __init__(self): 
        # Redis configuration 
        self.redis_client = None 
        AZURE_REDIS_ENDPOINT = os.getenv("AZURE_REDIS_ENDPOINT")  
        AZURE_REDIS_KEY = os.getenv("AZURE_REDIS_KEY")  
        if AZURE_REDIS_KEY: #use redis
            self.redis_client = redis.StrictRedis(host=AZURE_REDIS_ENDPOINT, port=6380, password=AZURE_REDIS_KEY, ssl=True)  
        else: #use in-memory
            self.session_store: Dict[str, Dict] = {}  

                
    def get(self, key):  
        print("getting state")
        if self.redis_client:
            self.data = self.redis_client.get(key)  
            return pickle.loads(base64.b64decode(self.data)) if self.data else None  
        else:
            return self.session_store.get(key)

          
    def set(self, key, value):  
        print("setting state")
        if self.redis_client:
            self.redis_client.set(key, base64.b64encode(pickle.dumps(value)))  
        else:
            self.session_store[key]=value
          
