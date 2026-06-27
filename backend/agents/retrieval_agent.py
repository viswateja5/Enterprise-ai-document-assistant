import logging
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

# Local imports
from agents.graph_state import AgentState
from utils.embeddings import get_embeddings_model
from utils.faiss_store import load_vector_store
from utils.search import create_hybrid_retriever
from utils.rerank import rerank_documents
from utils.query_processor import expand_query, extract_metadata_filters

def deduplicate_docs(docs: List[Document]) -> List[Document]:
    seen_content = set()
    deduped = []
    for doc in docs:
        content = doc.page_content.strip()
        if content not in seen_content:
            seen_content.add(content)
            deduped.append(doc)
    return deduped

logger = logging.getLogger("rag-backend")

async def retrieve_documents(state: AgentState) -> dict:
    """
    Retrieval agent node. Performs dynamic, session-aware, and metadata-aware RAG search.
    Implements query expansion, dynamic k targets, self-query filters, and multi-level fallbacks.
    """
    decision = state.get("decision", "llm")
    query = state.get("query", "").strip()
    reasoning_trace = state.get("reasoning_trace", [])
    
    if decision not in ["rag", "hybrid"]:
        return {"documents": [], "reasoning_trace": reasoning_trace}

    reasoning_trace.append("Retrieval Agent activated. Commencing hybrid retrieval pipeline...")
    
    # 1. Query Expansion (Improve recall)
    expanded_query_str = expand_query(query)
    if expanded_query_str != query:
        reasoning_trace.append(f"Query expanded to improve recall: '{expanded_query_str}'")

    # 2. Self-Query Metadata extraction
    session_id = state.get("session_id")
    global_search = state.get("global_search", False)
    
    available_filenames = []
    try:
        from database.connection import async_session_maker
        from sqlalchemy import select
        from models.db_models import UploadFileModel
        async with async_session_maker() as db:
            result = await db.execute(
                select(UploadFileModel.filename).where(
                    UploadFileModel.session_id == session_id
                )
            )
            available_filenames = [row[0] for row in result.all()]
    except Exception as dbe:
        logger.warning(f"Could not retrieve session filenames from database: {dbe}")

    page_filter, doc_filter = extract_metadata_filters(query, available_filenames)
    filter_messages = []
    if page_filter is not None:
        filter_messages.append(f"page={page_filter + 1}")
    if doc_filter is not None:
        filter_messages.append(f"document_name='{doc_filter}'")
    if filter_messages:
        reasoning_trace.append(f"Self-query filters extracted: {', '.join(filter_messages)}")

    # 3. Dynamic K selection based on classified query_type (capped to 3-5 chunks for low-latency)
    query_type = state.get("query_type", "fact")
    if query_type == "fact":
        candidate_k = 10
        top_n = 3
    else:
        candidate_k = 15
        top_n = 5
        
    reasoning_trace.append(f"Dynamic k configured: candidate_k={candidate_k}, rerank_top_k={top_n} (based on type '{query_type}').")

    # 4. Multi-level Fallback Chain execution
    vector_db = None
    try:
        embeddings = get_embeddings_model()
        vector_db = load_vector_store("vector_store", embeddings)
    except Exception as ve:
        logger.error(f"Vector store loading failed: {ve}", exc_info=True)
        reasoning_trace.append("Vector store is offline or failed to load. Falling back to direct LLM.")
        return {"documents": [], "reasoning_trace": reasoning_trace}

    retrieved_docs = []
    
    # --- Level 1: Ensemble Retrieval + Reranking ---
    try:
        retriever = create_hybrid_retriever(
            vector_db, 
            top_k=candidate_k, 
            session_id=session_id, 
            global_search=global_search,
            page=page_filter,
            document_name=doc_filter
        )
        candidates = await retriever.ainvoke(expanded_query_str)
        candidates = deduplicate_docs(candidates)
        reasoning_trace.append(f"Level 1: Retrieved {len(candidates)} unique candidates via hybrid EnsembleRetriever.")
        
        try:
            retrieved_docs = rerank_documents(expanded_query_str, candidates, top_n=top_n)
            retrieved_docs = deduplicate_docs(retrieved_docs)[:top_n]
            reasoning_trace.append(f"Level 1: Successfully reranked top {len(retrieved_docs)} chunks using CrossEncoder.")
            return {"documents": retrieved_docs, "reasoning_trace": reasoning_trace}
        except Exception as re:
            logger.warning(f"Reranker failed: {re}", exc_info=True)
            reasoning_trace.append(f"Level 1 Reranker failed. Falling back to Ensemble candidates: {re}")
            # --- Level 2: Ensemble direct output (Rerank fallback) ---
            return {"documents": candidates[:top_n], "reasoning_trace": reasoning_trace}
            
    except Exception as ee:
        logger.warning(f"EnsembleRetriever failed: {ee}", exc_info=True)
        reasoning_trace.append(f"EnsembleRetriever retrieval failed: {ee}. Falling back to FAISS only...")
        
        # --- Level 3: FAISS-only fallback ---
        try:
            search_kwargs = {"k": top_n * 2} # fetch extra for deduplication
            filter_dict = {}
            if not global_search and session_id:
                filter_dict["session_id"] = session_id
            if page_filter is not None:
                filter_dict["page"] = page_filter
            if doc_filter is not None:
                filter_dict["document_name"] = doc_filter
                
            if filter_dict:
                search_kwargs["filter"] = filter_dict
                
            faiss_retriever = vector_db.as_retriever(search_kwargs=search_kwargs)
            candidates = await faiss_retriever.ainvoke(expanded_query_str)
            retrieved_docs = deduplicate_docs(candidates)[:top_n]
            reasoning_trace.append(f"Level 3: Retrieved {len(retrieved_docs)} unique chunks using FAISS-only.")
            return {"documents": retrieved_docs, "reasoning_trace": reasoning_trace}
        except Exception as fe:
            logger.warning(f"FAISS fallback failed: {fe}", exc_info=True)
            reasoning_trace.append(f"Level 3 FAISS-only retrieval failed: {fe}. Falling back to BM25 only...")
            
            # --- Level 4: BM25-only fallback ---
            try:
                all_documents = list(vector_db.docstore._dict.values())
                if not global_search and session_id:
                    all_documents = [d for d in all_documents if d.metadata.get("session_id") == session_id]
                if page_filter is not None:
                    all_documents = [d for d in all_documents if d.metadata.get("page") == page_filter]
                if doc_filter is not None:
                    all_documents = [d for d in all_documents if d.metadata.get("document_name") == doc_filter]
                    
                if all_documents:
                    bm25 = BM25Retriever.from_documents(all_documents)
                    bm25.k = top_n * 2
                    candidates = await bm25.ainvoke(expanded_query_str)
                    retrieved_docs = deduplicate_docs(candidates)[:top_n]
                    reasoning_trace.append(f"Level 4: Retrieved {len(retrieved_docs)} unique chunks using BM25-only.")
                    return {"documents": retrieved_docs, "reasoning_trace": reasoning_trace}
                else:
                    reasoning_trace.append("Level 4 BM25 has no source documents. Defaulting to general LLM.")
                    return {"documents": [], "reasoning_trace": reasoning_trace}
            except Exception as be:
                logger.error(f"BM25 fallback failed: {be}", exc_info=True)
                reasoning_trace.append(f"Level 4 BM25-only retrieval failed: {be}. Defaulting to general LLM.")
                
                # --- Level 5: Fallback to LLM (Empty docs) ---
                return {"documents": [], "reasoning_trace": reasoning_trace}
