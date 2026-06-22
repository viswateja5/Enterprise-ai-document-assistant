import os
from functools import lru_cache
from typing import Any
from langchain_core.embeddings import Embeddings

@lru_cache(maxsize=1)
def get_embeddings_model() -> Embeddings:
    """
    Returns the cached instance of Embeddings.
    Checks environment keys for API-based embeddings first (which use almost zero RAM),
    falling back to a local CPU-based HuggingFace model if no keys are found.
    """
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and google_key != "your_google_api_key_here":
        try:
            from langchain_google_genai import GoogleGenAIEmbeddings
            return GoogleGenAIEmbeddings(
                model="models/embedding-001",
                google_api_key=google_key
            )
        except Exception as e:
            print(f"Failed to load GoogleGenAIEmbeddings: {e}. Trying fallback...")

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "your_openai_api_key_here":
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=openai_key
            )
        except Exception as e:
            print(f"Failed to load OpenAIEmbeddings: {e}. Trying fallback...")

    # Fallback to local HuggingFace embeddings
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

