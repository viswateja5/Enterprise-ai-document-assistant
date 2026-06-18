from functools import lru_cache
from typing import List
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document

@lru_cache(maxsize=1)
def get_cross_encoder() -> CrossEncoder:
    """
    Loads and caches the CrossEncoder reranker model.
    Using lru_cache ensures the model remains in memory after the first load.
    
    Returns:
        CrossEncoder: The initialized CrossEncoder model.
    """
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
    
    Args:
        query (str): The search question.
        documents (List[Document]): Retrieved candidate documents (e.g. from hybrid search).
        top_n (int): Target number of documents to return. Defaults to 4.
        
    Returns:
        List[Document]: The top N semantically relevant documents sorted by relevance.
    """
    if not documents:
        return []
        
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
