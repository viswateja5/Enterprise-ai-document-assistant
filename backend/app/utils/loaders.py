import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_core.documents import Document

def load_document(file_path: str) -> List[Document]:
    """
    Loads text content from a file and returns a list of Document objects.
    Supports PDF, DOCX, and TXT.
    
    Args:
        file_path (str): The local path to the file.
        
    Returns:
        List[Document]: List of parsed Document elements.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If file extension is unsupported or loading fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Document file not found at: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".docx":
        # Requires docx2txt package
        loader = Docx2txtLoader(file_path)
    elif ext == ".txt":
        # Force UTF-8 encoding to support international characters
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(
            f"Unsupported file extension '{ext}'. Only PDF, DOCX, and TXT are supported."
        )
        
    try:
        documents = loader.load()
        if not documents or not any(doc.page_content.strip() for doc in documents):
            raise ValueError("Document appears to be empty or contains no extractable text.")
        return documents
    except Exception as e:
        raise ValueError(f"Failed to parse document: {str(e)}") from e
