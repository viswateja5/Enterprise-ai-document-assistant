import os
import logging
from typing import List
import httpx
from langchain_core.documents import Document

logger = logging.getLogger("rag-backend")

async def search_tavily(query: str) -> List[Document]:
    """
    Queries Tavily Search API to retrieve web search results when semantic 
    confidence in indexed local documents is too low.
    
    Args:
        query (str): The search query.
        
    Returns:
        List[Document]: Web results converted into standard Document items.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.warning(
            "Tavily search fallback triggered but TAVILY_API_KEY is not defined in .env."
        )
        return []
        
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic"
    }
    
    try:
        logger.info(f"Triggering Tavily Web Search fallback for query: '{query}'")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(
                    f"Tavily search request failed with code {response.status_code}: {response.text}"
                )
                return []
                
            data = response.json()
            results = data.get("results", [])
            
            documents = []
            for item in results:
                # Wrap each web search result into a standard LangChain Document object
                doc = Document(
                    page_content=item.get("content", ""),
                    metadata={
                        "source": item.get("url", "web_search"),
                        "title": item.get("title", "Web Result"),
                        "page": 0,  # 0 indicates web source rather than PDF page number
                        "is_web": True
                    }
                )
                documents.append(doc)
                
            logger.info(f"Tavily Search completed. Found {len(documents)} results.")
            return documents
            
    except Exception as e:
        logger.error(f"Tavily search client exception: {str(e)}", exc_info=True)
        return []
