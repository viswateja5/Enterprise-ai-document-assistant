import os
from typing import Any
from langchain_openai import ChatOpenAI

def get_llm(streaming: bool = True) -> Any:
    """
    Dynamically instantiates and returns the configured LLM provider client
    based on the MODEL_PROVIDER environment variable.
    
    Supported values: 'openai', 'gemini', 'groq', 'ollama'
    """
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing.")
        return ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.0, 
            streaming=streaming,
            openai_api_key=api_key
        )
        
    elif provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")
        # Lazy import to avoid loading unused packages
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash", 
            google_api_key=api_key, 
            temperature=0.0, 
            streaming=streaming
        )
        
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")
        from langchain_groq import ChatGroq
        return ChatGroq(
           model="llama-3.3-70b-versatile", 
            groq_api_key=api_key, 
            temperature=0.0, 
            streaming=streaming
        )
        
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        return ChatOllama(
            model="llama3", 
            base_url=ollama_host, 
            temperature=0.0
        )
        
    else:
        raise ValueError(
            f"Unsupported MODEL_PROVIDER '{provider}'. "
            f"Supported options are: 'openai', 'gemini', 'groq', 'ollama'"
        )
