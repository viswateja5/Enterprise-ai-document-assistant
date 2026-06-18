from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request, status
from slowapi import Limiter

# Local imports
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.rag import UploadResponse
from app.services import rag_service
from app.api.auth import get_current_user

upload_router = APIRouter(tags=["Document Ingestion"])

@upload_router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,  # Required by slowapi to evaluate request context/IP
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests PDF, DOCX, or TXT documents, computes embeddings and updates vector index.
    
    Guarded by:
    - User Authentication (Bearer Token)
    - Rate Limiting (5 requests per minute)
    """
    # Verify file extension format
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx") or filename_lower.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF, DOCX, and TXT files are accepted."
        )
        
    try:
        total_chunks = await rag_service.ingest_document(file)
        return UploadResponse(
            filename=file.filename,
            message="Document uploaded, parsed, embedded, and added to ensemble hybrid store successfully.",
            total_chunks=total_chunks
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Incompatible document structure: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while uploading file: {str(e)}"
        )
