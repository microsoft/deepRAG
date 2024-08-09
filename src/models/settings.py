from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Settings for the application"""
    openai_endpoint: str = Field(validation_alias='AZURE_OPENAI_ENDPOINT')
    openai_key: str = Field(validation_alias='AZURE_OPENAI_API_KEY')
    openai_embedding_deployment: str = Field(validation_alias='AZURE_OPENAI_EMB_DEPLOYMENT')
    openai_chat_deployment: str = Field(validation_alias='AZURE_OPENAI_CHAT_DEPLOYMENT')
    openai_api_version: str = Field(validation_alias='AZURE_OPENAI_API_VERSION')
    azure_search_endpoint: str = Field(validation_alias='AZURE_SEARCH_ENDPOINT')
    azure_search_key: str = Field(validation_alias='AZURE_SEARCH_KEY')
    azure_search_index_name: str = Field(validation_alias='AZURE_SEARCH_INDEX_NAME')
    azure_vision_key: str = Field(validation_alias='AZURE_AI_VISION_API_KEY')
    azure_vision_endpoint: str = Field(validation_alias='AZURE_AI_VISION_ENDPOINT')
    smart_agent_prompt_location: str = Field(validation_alias='SMART_AGENT_PROMPT_LOCATION')
    smart_agent_image_path: str = Field(validation_alias='IMAGE_PATH')
    azure_redis_endpoint: str = Field(validation_alias='AZURE_REDIS_ENDPOINT')
    azure_redis_key: str = Field(validation_alias='AZURE_REDIS_KEY')
    azure_storage_account_key: str = Field(validation_alias='AZURE_STORAGE_ACCOUNT_KEY')  
    azure_storage_account_name: str = Field(validation_alias='AZURE_STORAGE_ACCOUNT_NAME')  
    azure_container_name: str = Field(validation_alias='AZURE_CONTAINER_NAME')  
    api_port: int = Field(validation_alias='API_PORT', default='8080')
    app_port: int = Field(validation_alias='APP_PORT', default='8000')
    app_host: str = Field(validation_alias='APP_HOST', default='localhost')
    api_host: str = Field(validation_alias='API_HOST', default='localhost')
