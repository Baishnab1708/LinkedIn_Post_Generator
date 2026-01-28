from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: str 
    azure_openai_api_key: str 
    azure_openai_deployment: str 
    azure_openai_api_version: str 
    
    # Temperature settings for different modes
    similar_mode_temperature: float = 0.3  # Lower creativity for consistent style
    different_mode_temperature: float = 0.7  # Higher creativity for unique posts
    
    # Qdrant Configuration
    qdrant_path: str = "./qdrant_db"  # Local persistent storage path
    qdrant_collection_name: str = "linkedin_posts"
    
    # Post Configuration
    max_post_length: int = 3000  # LinkedIn character limit
    min_post_length: int = 100
    
    # Memory Configuration
    similarity_threshold: float = 0.75  # Threshold for "similar topic" detection
    max_similar_posts_to_retrieve: int = 3
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
