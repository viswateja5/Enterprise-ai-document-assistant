from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter

# Local imports
from app.core.rate_limit import limiter
from app.core.database import get_db, async_session_maker
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.schemas.rag import QueryRequest, ChatSessionResponse
from app.services import rag_service
from app.api.auth import get_current_user

query_router = APIRouter(tags=["Document Search & Chat"])

@query_router.post("/query")
@limiter.limit("20/minute")
async def query_documents(
    request: Request,  # Required by slowapi key resolver
    body: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Evaluates questions against document indexes using a hybrid search and reranking flow,
    streaming the generated answer back as JSON lines in real-time.
    
    Guarded by:
    - User Authentication (Bearer Token)
    - Rate Limiting (20 requests per minute)
    
    Stream JSON Structure:
    - `{"type": "sources", "data": [{"filename": "doc.pdf", "page": 1}]}`
    - `{"type": "content", "data": "word"}`
    - `{"type": "done"}`
    """
    return StreamingResponse(
        rag_service.query_rag_stream(
            query=body.question,
            session_id=body.session_id,
            user_id=current_user.id,
            session_maker=async_session_maker
        ),
        media_type="text/event-stream"
    )

@query_router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def get_user_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns list of all active conversational chat sessions for the authenticated user.
    """
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    
    # Format and convert models to match schema output (property getter handles sources list conversion)
    formatted = []
    for sess in sessions:
        msgs = [
            {
                "role": m.role,
                "content": m.content,
                "sources": m.sources,  # uses getter property mapping JSON to List
                "created_at": m.created_at
            }
            for m in sess.messages
        ]
        formatted.append({
            "id": sess.id,
            "name": sess.name,
            "created_at": sess.created_at,
            "messages": msgs
        })
        
    return formatted

@query_router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session_details(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches full message logs and citation metadata for a single session ID.
    """
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{session_id}' not found."
        )
        
    msgs = [
        {
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "created_at": m.created_at
        }
        for m in session.messages
    ]
    
    return {
        "id": session.id,
        "name": session.name,
        "created_at": session.created_at,
        "messages": msgs
    }
