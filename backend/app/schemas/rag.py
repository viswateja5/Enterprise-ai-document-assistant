from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class QueryRequest(BaseModel):
    question: str = Field(..., description="User question to evaluate against document collections.")
    session_id: str = Field(..., description="Unique conversation session ID.")

class SourceMetadata(BaseModel):
    filename: str = Field(..., description="Name of the source document.")
    page: int = Field(..., description="1-indexed page number in the source file.")

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

class QueryResponse(BaseModel):
    answer: str = Field(..., description="The generated grounded answer from the assistant.")
    sources: List[SourceMetadata] = Field(..., description="Annotated source document pages citation chips.")
    chat_history: List[ChatMessageResponse] = Field(default_factory=list, description="Updated message exchange logs in the active session.")
