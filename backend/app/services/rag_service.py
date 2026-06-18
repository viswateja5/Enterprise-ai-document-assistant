import os
import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
import redis.asyncio as aioredis

from langchain_core.documents import Document
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_openai import ChatOpenAI

# Local imports
from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage
from app.utils.loaders import load_document
from app.utils.embeddings import get_embeddings_model
from app.utils.faiss_store import save_or_update_vector_store, load_vector_store
from app.utils.search import create_hybrid_retriever
from app.utils.rerank import rerank_documents

logger = logging.getLogger("rag-backend")

# Global Redis async client
redis_client: Optional[aioredis.Redis] = None
local_cache: Dict[str, Any] = {}

async def init_redis() -> None:
    """
    Initializes the async Redis client. Falls back to local memory if connection fails.
    """
    global redis_client
    try:
        # Connect to Redis using config URL
        redis_client = aioredis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True,
            socket_timeout=2.0
        )
        await redis_client.ping()
        logger.info("Connected to Redis cache successfully.")
    except Exception as e:
        logger.warning(
            f"Redis connection failed (caching will fallback to local in-memory dict): {str(e)}"
        )
        redis_client = None

async def get_cached_response(key: str) -> Optional[Dict[str, Any]]:
    """
    Fetches cached result from Redis or in-memory fallback.
    """
    if redis_client:
        try:
            val = await redis_client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis cache fetch failed: {str(e)}")
    return local_cache.get(key)

async def set_cached_response(key: str, data: Dict[str, Any], expire_seconds: int = 3600) -> None:
    """
    Sets response inside cache with expiration window.
    """
    if redis_client:
        try:
            await redis_client.setex(key, expire_seconds, json.dumps(data))
            return
        except Exception as e:
            logger.warning(f"Redis cache save failed: {str(e)}")
    local_cache[key] = data

# --- RAG Ingestion & Query Logic ---

async def ingest_document(file: UploadFile) -> int:
    """
    Ingests PDF, DOCX, or TXT document, generating chunks, embeddings, and updating FAISS.
    
    Returns:
        int: The number of generated text chunks.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    
    # Save file stream locally
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 1. Parse text using our multi-format loaders
        documents = load_document(file_path)
        
        # 2. Split text using RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True
        )
        chunks = splitter.split_documents(documents)
        
        if not chunks:
            raise ValueError("No text chunks could be generated from the document.")
            
        # 3. Embed and save to FAISS database
        embeddings = get_embeddings_model()
        save_or_update_vector_store(chunks, embeddings, settings.STORE_DIR)
        
        return len(chunks)
    except Exception as e:
        # Clean up files if processing failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e

async def get_or_create_session(
    db: AsyncSession, 
    session_id: str, 
    user_id: int
) -> ChatSession:
    """
    Gets or registers a ChatSession for a user.
    """
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalars().first()
    
    if not session:
        session = ChatSession(id=session_id, name="New Conversation", user_id=user_id)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
    return session

async def query_rag_stream(
    query: str,
    session_id: str,
    user_id: int,
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[str, None]:
    """
    RAG generation pipeline returning an async text stream yield.
    
    Yields output JSON strings:
    - type: "sources" -> list of source dicts
    - type: "content" -> response token
    - type: "done" -> final signal
    """
    # 1. Check cache first to avoid LLM & db overheads
    cache_key = f"rag_cache:{user_id}:{session_id}:{query.strip().lower()}"
    cached = await get_cached_response(cache_key)
    
    if cached:
        logger.info(f"Serving RAG query from cache for session {session_id}")
        yield json.dumps({"type": "sources", "data": cached["sources"]}) + "\n"
        # Yield the full cached answer in one go (standard streaming fallback)
        yield json.dumps({"type": "content", "data": cached["answer"]}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    # Initialize isolated database session for stream duration
    async with session_maker() as db:
        # Retrieve or create session context
        session = await get_or_create_session(db, session_id, user_id)
        
        # Save User Message to SQLite
        user_msg = ChatMessage(session_id=session_id, role="user", content=query)
        db.add(user_msg)
        await db.commit()
        
        # Load local FAISS vector store
        embeddings = get_embeddings_model()
        try:
            vector_db = load_vector_store(settings.STORE_DIR, embeddings)
        except FileNotFoundError:
            # Handle empty vector database gracefully
            yield json.dumps({"type": "sources", "data": []}) + "\n"
            err_msg = "No documents have been uploaded yet. Please upload a PDF, DOCX, or TXT file first."
            yield json.dumps({"type": "content", "data": err_msg}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            
            # Save error response to db
            bot_msg = ChatMessage(session_id=session_id, role="assistant", content=err_msg)
            db.add(bot_msg)
            await db.commit()
            return
            
        # 2. Execute Hybrid Retrieval (BM25 + FAISS)
        # Pull 10 candidate document chunks
        retriever = create_hybrid_retriever(vector_db, top_k=10)
        retrieved_docs = await retriever.ainvoke(query)
        
        # 3. Perform Cross-Encoder Reranking
        # Filter down to the top K=4 chunks
        reranked_docs = rerank_documents(query, retrieved_docs, top_n=4)
        
        # Format sources citation details
        sources_list = []
        seen = set()
        for doc in reranked_docs:
            full_path = doc.metadata.get("source", "unknown")
            filename = os.path.basename(full_path)
            page = doc.metadata.get("page", 0) + 1
            key = (filename, page)
            if key not in seen:
                seen.add(key)
                sources_list.append({"filename": filename, "page": page})
                
        # Yield sources metadata first so UI updates immediately
        yield json.dumps({"type": "sources", "data": sources_list}) + "\n"

        # 4. Construct context prompt with chat history
        history_str = ""
        # Fetch last 6 message lines to keep prompt size optimized
        for msg in session.messages[-7:-1]: # exclude the user message we just inserted
            history_str += f"{msg.role.capitalize()}: {msg.content}\n"
            
        context_str = "\n\n".join([
            f"[Source: {os.path.basename(d.metadata.get('source', 'unknown'))}, Page: {d.metadata.get('page', 0) + 1}]:\n{d.page_content}"
            for d in reranked_docs
        ])
        
        prompt_text = (
            "You are an AI assistant designed to help search documents.\n"
            "Answer the user's question using ONLY the provided document context below.\n"
            "If you do not know the answer or if the answer is not present in the context, "
            "reply exactly with: 'I do not have access to that information in the uploaded documents.'\n"
            "Do not make up facts, use outside knowledge, or extrapolate. Answer clearly and concisely.\n\n"
            f"Chat History:\n{history_str}\n"
            f"Document Context:\n{context_str}\n\n"
            f"User Question: {query}\n"
            "Answer:"
        )

        # 5. Execute Async LLM streaming
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            streaming=True
        )

        answer_text = ""
        try:
            # Stream response chunk-by-chunk
            async for chunk in llm.astream(prompt_text):
                token = chunk.content
                if token:
                    answer_text += token
                    yield json.dumps({"type": "content", "data": token}) + "\n"
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}", exc_info=True)
            yield json.dumps({"type": "content", "data": f"\n[Generation Error: {str(e)}]"}) + "\n"
            answer_text += f"\n[Generation Error: {str(e)}]"

        yield json.dumps({"type": "done"}) + "\n"

        # 6. Save Assistant response with citation list to DB
        bot_msg = ChatMessage(session_id=session_id, role="assistant", content=answer_text)
        bot_msg.sources = sources_list
        db.add(bot_msg)
        await db.commit()
        
        # 7. Cache the successfully generated result
        cache_data = {
            "answer": answer_text,
            "sources": sources_list
        }
        await set_cached_response(cache_key, cache_data, expire_seconds=3600)
