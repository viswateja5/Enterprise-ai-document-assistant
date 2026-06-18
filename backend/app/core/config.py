import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Search for .env in the parent root directory
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "Enterprise AI Document Assistant"
    
    # SQLite Database connection string (async using aiosqlite driver)
    # Stored inside the vector_store directory to inherit volume persistence automatically.
    DATABASE_URL: str = "sqlite+aiosqlite:///vector_store/chat_history.db"
    
    # JWT Authentication settings
    JWT_SECRET_KEY: str = "98782a8fb3a24564c76b9116e045cb2119ef0052baae9893d9ce1cf0f80bb150"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    
    # OpenAI & Redis Settings
    OPENAI_API_KEY: str = ""
    REDIS_URL: str = "redis://redis:6379/0"  # Configured to talk to the redis service inside docker compose
    
    # Storage settings
    UPLOAD_DIR: str = "./uploads"
    STORE_DIR: str = "./vector_store"
    
    # Chunking configurations
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

settings = Settings()
