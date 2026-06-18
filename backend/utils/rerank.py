from functools import lru_cache
from typing import List
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document

@lru_cache(maxsize=1)
def get_cross_encoder() -> CrossEncoder:
    """
    Loads and caches the CrossEncoder reranker model.
    """
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")

def rerank_documents(
    query: str,
    documents: List[Document],
    top_n: int = 4
) -> List[Document]:
    """
    Reranks candidate documents against a query using a CrossEncoder.
    """
    if not documents:
        return []
        
    model = get_cross_encoder()
    
    pairs = [[query, doc.page_content] for doc in documents]
    scores = model.predict(pairs)
    
    paired_docs = list(zip(documents, scores))
    paired_docs.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for doc, score in paired_docs[:top_n]:
        # Inject the rerank relevance score into document metadata
        doc.metadata["rerank_score"] = float(score)
        results.append(doc)
        
    return results
