from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter

# Local imports
from database.connection import get_db, async_session_maker
from core.rate_limit import limiter
from models.db_models import User, ChatSession
from schemas.api_schemas import UploadResponse, QueryRequest, ChatSessionResponse
from services import rag_engine
from routers.auth import get_current_user

rag_router = APIRouter(tags=["Document Search & Chat"])

@rag_router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,  # Required by slowapi
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests a document (PDF, DOCX, or TXT).
    Guarded by:
    - JWT authentication
    - Rate limiting (5 requests/minute)
    """
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx") or filename_lower.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension. Only PDF, DOCX, and TXT files are accepted."
        )
        
    try:
        total_chunks = await rag_engine.ingest_document(file, current_user.id, db)
        return UploadResponse(
            filename=file.filename,
            message="Document uploaded and processed successfully.",
            total_chunks=total_chunks
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failure: {str(e)}"
        )

@rag_router.post("/query")
@limiter.limit("20/minute")
async def query_documents(
    request: Request,  # Required by slowapi
    body: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Streams RAG answers token-by-token using Server-Sent Events.
    Guarded by:
    - JWT authentication
    - Rate limiting (20 requests/minute)
    """
    return StreamingResponse(
        rag_engine.query_rag_stream(
            query=body.question,
            session_id=body.session_id,
            user_id=current_user.id,
            session_maker=async_session_maker
        ),
        media_type="text/event-stream"
    )

@rag_router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches all conversational sessions for the current authenticated user.
    """
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    
    formatted = []
    for sess in sessions:
        msgs = [
            {
                "role": m.role,
                "content": m.content,
                "sources": m.sources,
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

@rag_router.get("/history/{session_id}", response_model=ChatSessionResponse)
async def get_session_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full message log history for a specific session ID.
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

@rag_router.delete("/session/{id}", status_code=status.HTTP_200_OK)
async def delete_chat_session(
    id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently deletes a chat session and all its associated messages logs.
    """
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == id, ChatSession.user_id == current_user.id)
    )
    session = result.scalars().first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session '{id}' not found."
        )
        
    # Remove from LangChain buffer memory cache too
    from memory.memory_manager import clear_session_memory
    clear_session_memory(id)
    
    await db.execute(delete(ChatSession).where(ChatSession.id == id))
    await db.commit()
    
    return {"message": f"Chat session '{id}' successfully deleted."}
