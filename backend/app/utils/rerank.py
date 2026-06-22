from functools import lru_cache
from typing import List, Any
from langchain_core.documents import Document

@lru_cache(maxsize=1)
def get_cross_encoder() -> Any:
    """
    Loads and caches the CrossEncoder reranker model.
    Using lru_cache ensures the model remains in memory after the first load.
    
    Returns:
        CrossEncoder: The initialized CrossEncoder model.
    """
    from sentence_transformers import CrossEncoder
    # Using 'cross-encoder/ms-marco-MiniLM-L-6-v2' which is a standard, 
    # highly efficient model optimized for passages/query search reranking.
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")

def rerank_documents(
    query: str,
    documents: List[Document],
    top_n: int = 4
) -> List[Document]:
    """
    Reranks a list of candidate documents against a query using a CrossEncoder.
    If the CrossEncoder cannot be initialized or fails, falls back gracefully.
    
    Args:
        query (str): The search question.
        documents (List[Document]): Retrieved candidate documents.
        top_n (int): Target number of documents to return. Defaults to 4.
        
    Returns:
        List[Document]: The top N semantically relevant documents sorted by relevance.
    """
    if not documents:
        return []
        
    if len(documents) <= 1:
        documents[0].metadata["rerank_score"] = 1.0
        return documents[:top_n]
        
    try:
        model = get_cross_encoder()
        
        # Format pairs as expected by the cross-encoder: [[query, passage_1], [query, passage_2], ...]
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Compute relevance scores
        scores = model.predict(pairs)
        
        # Pair documents with their calculated scores
        paired_docs = list(zip(documents, scores))
        
        # Sort paired documents by score in descending order (highest relevance first)
        paired_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Select the top_n results
        results = []
        for doc, score in paired_docs[:top_n]:
            # Inject the rerank relevance score into document metadata for debugging
            doc.metadata["rerank_score"] = float(score)
            results.append(doc)
            
        return results
    except Exception as e:
        # Graceful fallback: return the original order with simulated scores
        import logging
        logger = logging.getLogger("rerank")
        logger.warning(f"Reranking failed or disabled (using direct fallback): {e}")
        for idx, doc in enumerate(documents):
            doc.metadata["rerank_score"] = 1.0 - (idx * 0.05)
        return documents[:top_n]

