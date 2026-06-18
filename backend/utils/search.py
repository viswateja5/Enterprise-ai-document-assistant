from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

def create_hybrid_retriever(
    db: FAISS,
    top_k: int = 10
) -> EnsembleRetriever:
    """
    Creates an EnsembleRetriever combining BM25 (sparse keyword search) 
    and FAISS (dense semantic search).
    """
    all_documents = list(db.docstore._dict.values())
    
    if not all_documents:
        raise ValueError("Cannot initialize retriever: FAISS index is empty.")
    
    # 1. Setup Dense Retriever (FAISS)
    dense_retriever = db.as_retriever(search_kwargs={"k": top_k})
    
    # 2. Setup Sparse Retriever (BM25)
    sparse_retriever = BM25Retriever.from_documents(all_documents)
    sparse_retriever.k = top_k
    
    # 3. Fuse using EnsembleRetriever with Reciprocal Rank Fusion (RRF)
    # Applying equal weight coefficients (0.5 each)
    ensemble_retriever = EnsembleRetriever(
        retrievers=[sparse_retriever, dense_retriever],
        weights=[0.5, 0.5]
    )
    
    return ensemble_retriever
