import base64
import pickle
from distributed_cache.cache import Cache

class History:
    """History class"""

    def __init__(self, session_id: str, cache: Cache):
        """Constructor for History"""
        self.__session_id: str = session_id
        self.__cache: Cache = cache

    def set_history(self, history):
        """Set the history"""
        self.__cache.set(self.__session_id, base64.b64encode(pickle.dumps(history)))

    def clean_up_history(self, max_q_with_detail_hist=1, max_q_to_keep=2):
        """Clean up the history"""

        cache_history = self.__cache.get(self.__session_id)

        if cache_history is None:
            return
        
        history = pickle.loads(base64.b64decode(cache_history))
        question_count=0
        removal_indices=[]

        for idx in range(len(history)-1, 0, -1):
            message = dict(history[idx])

            if message.get("role") == "user":
                question_count +=1

            if question_count>= max_q_with_detail_hist and question_count < max_q_to_keep:
                if message.get("role") != "user" and message.get("role") != "assistant" and len(message.get("content")) == 0:
                    removal_indices.append(idx)

            if question_count >= max_q_to_keep:
                removal_indices.append(idx)
        
        # remove items with indices in removal_indices
        for index in removal_indices:
            del history[index]

    def reset_history_to_last_question(self):
        """Reset the history to the last question"""

        cache_history = self.__cache.get(self.__session_id)

        if cache_history is None:
            return
        
        history = pickle.loads(base64.b64decode(cache_history))
        
        for i in range(len(history)-1, -1, -1):
            message = dict(history[i])   
            
            if message.get("role") == "user":
                break
            
            history.pop()

        self.__cache.set(self.__session_id, base64.b64encode(pickle.dumps(history)))

