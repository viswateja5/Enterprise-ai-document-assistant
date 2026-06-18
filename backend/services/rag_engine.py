import os
import json
import logging
import uuid
from typing import AsyncGenerator, List, Dict, Any, Optional
from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from langchain_core.documents import Document

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

# Local utility and service imports
from database.connection import async_session_maker
from models.db_models import User, ChatSession, ChatMessage, UploadFileModel
from utils.loaders import load_document
from utils.embeddings import get_embeddings_model
from utils.faiss_store import save_or_update_vector_store, load_vector_store
from utils.search import create_hybrid_retriever
from utils.rerank import rerank_documents
from services.llm_factory import get_llm
from services.web_search import search_tavily
from cache.redis_cache import get_cached, set_cached

logger = logging.getLogger("rag-backend")

# In-memory query counter for admin stats
_query_count = 0

async def ingest_document(file: UploadFile, user_id: int, db: AsyncSession) -> int:
    """
    Saves and processes an uploaded document (PDF, DOCX, or TXT).
    Saves metadata to database and updates local FAISS vector store.
    """
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    
    # Save the file stream
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 1. Parse text using our custom loaders
        documents = load_document(file_path)
        
        # 2. Split text using RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            add_start_index=True
        )
        chunks = splitter.split_documents(documents)
        
        if not chunks:
            raise ValueError("No text chunks could be extracted from the document.")
            
        # 3. Generate embeddings and save to local FAISS store
        embeddings = get_embeddings_model()
        save_or_update_vector_store(chunks, embeddings, "vector_store")
        
        # 4. Save metadata record to database
        db_file = UploadFileModel(
            filename=file.filename,
            user_id=user_id,
            chunk_count=len(chunks)
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)
        
        logger.info(f"Ingested {file.filename}. Chunks generated: {len(chunks)}")
        return len(chunks)
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Ingestion failed for {file.filename}: {e}", exc_info=True)
        raise e

async def get_or_create_session(
    db: AsyncSession, 
    session_id: str, 
    user_id: int
) -> ChatSession:
    """
    Retrieves or creates a ChatSession record in the database.
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
    Main conversational RAG stream generator.
    Retrieves top candidate chunks via hybrid search, reranks using Cross-Encoder,
    optionally triggers Tavily Search if confidence is below threshold,
    and returns a Server-Sent Events JSON stream with source citation tags.
    """
    global _query_count
    _query_count += 1
    
    # 1. Evaluate cache
    cache_key = f"enterprise_cache:{user_id}:{session_id}:{query.strip().lower()}"
    cached = await get_cached(cache_key)
    
    if cached:
        logger.info(f"RAG query cache hit for key: {cache_key}")
        yield json.dumps({"type": "sources", "data": cached["sources"]}) + "\n"
        yield json.dumps({"type": "content", "data": cached["answer"]}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"
        return

    # Initialize async database session for query flow
    async with session_maker() as db:
        session = await get_or_create_session(db, session_id, user_id)
        
        # Save User Message log
        user_msg = ChatMessage(session_id=session_id, role="user", content=query)
        db.add(user_msg)
        await db.commit()
        
        # Load Vector Store
        embeddings = get_embeddings_model()
        faiss_active = True
        vector_db = None
        try:
            vector_db = load_vector_store("vector_store", embeddings)
        except Exception:
            faiss_active = False
            
        reranked_docs = []
        is_web_fallback = False
        
        # 2. Candidate Retrieval
        if faiss_active and vector_db:
            try:
                # Retrieve top 10 candidate document chunks via hybrid (BM25 + FAISS)
                retriever = create_hybrid_retriever(vector_db, top_k=10)
                retrieved_docs = await retriever.ainvoke(query)
                
                # 3. Cross-Encoder Reranking
                # Filter down to the top K=10 chunks
                reranked_docs = rerank_documents(query, retrieved_docs, top_n=10)
            except Exception as e:
                logger.error(f"Hybrid retrieval or reranking failed: {e}")
                
        # 4. Confidence Threshold Check & Web Search Fallback
        # If the highest score is below -2.0 (low confidence) or if FAISS is offline,
        # we trigger the Tavily Search API wrapper fallback.
        best_score = reranked_docs[0].metadata.get("rerank_score", -99.0) if reranked_docs else -99.0
        
        # Check threshold
        if not reranked_docs or best_score < -2.0:
            logger.info(f"Confidence score {best_score} is below threshold. Running Web Search Fallback...")
            web_docs = await search_tavily(query)
            if web_docs:
                reranked_docs = web_docs[:4]
                is_web_fallback = True

        # Format source citations list
        sources_list = []
        seen = set()
        for idx, doc in enumerate(reranked_docs):
            full_path = doc.metadata.get("source", "unknown")
            filename = os.path.basename(full_path)
            page = doc.metadata.get("page", 0) + 1 if not doc.metadata.get("is_web") else 0
            
            # Generate a stable chunk_id
            chunk_hash = f"{filename}_{page}_{idx}"
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_hash))
            
            key = (filename, page)
            if key not in seen:
                seen.add(key)
                sources_list.append({
                    "file": filename,
                    "page": str(page) if page > 0 else "Web",
                    "chunk_id": chunk_id
                })
                
        # Yield sources info first
        yield json.dumps({"type": "sources", "data": sources_list}) + "\n"

        # 5. Build prompt incorporating history
        history_str = ""
        # Fetch last 6 message lines to keep prompt size optimized
        for msg in session.messages[-7:-1]:
            history_str += f"{msg.role.capitalize()}: {msg.content}\n"
            
        context_str = "\n\n".join([
            f"[Source: {os.path.basename(d.metadata.get('source', 'unknown'))}, Page: {d.metadata.get('page', 0) + 1}]:\n{d.page_content}"
            for d in reranked_docs
        ])
        
        prompt_text = (
            "You are an AI assistant designed to help search documents.\n"
            "Answer the user's question using ONLY the provided document context below.\n"
            "If the answer is not present in the context, reply exactly with: "
            "'I could not find relevant information in the uploaded documents.'\n"
            "Do not make up facts, use outside knowledge, or hallucinate. Be concise and precise.\n\n"
            f"Chat History:\n{history_str}\n"
            f"Document Context:\n{context_str}\n\n"
            f"User Question: {query}\n"
            "Answer:"
        )

        # 6. Stream tokens
        answer_text = ""
        try:
            llm = get_llm(streaming=True)
            # astream works for OpenAI, Groq, and Gemini
            async for chunk in llm.astream(prompt_text):
                token = chunk.content
                if token:
                    answer_text += token
                    yield json.dumps({"type": "content", "data": token}) + "\n"
        except Exception as e:
            logger.error(f"Streaming token generation failed: {e}", exc_info=True)
            yield json.dumps({"type": "content", "data": f"\n[Generation Error: {str(e)}]"}) + "\n"
            answer_text += f"\n[Generation Error: {str(e)}]"
            
        yield json.dumps({"type": "done"}) + "\n"

        # 7. Save Assistant message with citations to database
        bot_msg = ChatMessage(session_id=session_id, role="assistant", content=answer_text)
        bot_msg.sources = sources_list
        db.add(bot_msg)
        await db.commit()
        
        # 8. Cache response
        cache_data = {
            "answer": answer_text,
            "sources": sources_list
        }
        await set_cached(cache_key, cache_data, expire_seconds=3600)

async def get_db_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Aggregates metrics counts from database tables for the Admin analytics dashboard.
    """
    total_users_q = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_q.scalar() or 0
    
    total_chats_q = await db.execute(select(func.count()).select_from(ChatSession))
    total_chats = total_chats_q.scalar() or 0
    
    uploaded_docs_q = await db.execute(select(func.count()).select_from(UploadFileModel))
    uploaded_docs = uploaded_docs_q.scalar() or 0
    
    chunks_q = await db.execute(select(func.sum(UploadFileModel.chunk_count)))
    total_chunks = chunks_q.scalar() or 0
    
    return {
        "total_users": total_users,
        "total_chats": total_chats,
        "uploaded_documents": uploaded_docs,
        "number_of_chunks": int(total_chunks),
    }

def get_query_count() -> int:
    """
    Returns total query executions in the current session.
    """
    return _query_count
