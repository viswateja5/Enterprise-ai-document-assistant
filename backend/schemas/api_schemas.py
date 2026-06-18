from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

# --- Authentication Schemas ---

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, max_length=100, description="Account password")

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- RAG Schemas ---

class QueryRequest(BaseModel):
    question: str = Field(..., description="User query text context")
    session_id: str = Field(..., description="Unique conversation session ID")

class SourceMetadata(BaseModel):
    file: str = Field(..., description="Name of the source document file")
    page: int = Field(..., description="1-indexed page index location")
    chunk_id: str = Field(..., description="Internal hash metadata for the retrieved document chunk")

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    role: str
    content: str
    sources: List[SourceMetadata] = Field(default_factory=list)
    created_at: datetime

class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    created_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)

class UploadResponse(BaseModel):
    filename: str
    message: str
    total_chunks: int

# --- Admin Analytics Schemas ---

class AdminStatsResponse(BaseModel):
    total_users: int = Field(..., description="Total users registered in SQLite/Postgres DB")
    total_chats: int = Field(..., description="Total conversational sessions registered")
    uploaded_documents: int = Field(..., description="Total files uploaded by users")
    number_of_chunks: int = Field(..., description="Estimated total count of document vector blocks")
    query_count: int = Field(..., description="Total query requests logged")
    cache_hits: int = Field(..., description="Total cache queries served from Redis")
    average_response_time: float = Field(..., description="Mean response latency in seconds")

# --- Health check Schema ---

class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    redis_connected: bool
    supported_models: List[str]
