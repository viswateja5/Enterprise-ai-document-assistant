from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from database.connection import get_db
from models.db_models import User
from schemas.api_schemas import AdminStatsResponse
from services import rag_engine
from cache.redis_cache import get_cache_hits
from monitoring.metrics import get_average_response_time
from routers.auth import get_current_user

admin_router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])

@admin_router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns analytics aggregates for the Admin Dashboard:
    - total_users
    - total_chats
    - uploaded_documents
    - number_of_chunks
    - query_count
    - cache_hits
    - average_response_time (seconds)
    
    Guarded by:
    - User Authentication (Bearer Token)
    """
    # Query database counts
    db_metrics = await rag_engine.get_db_stats(db)
    
    # Retrieve runtime counters
    query_count = rag_engine.get_query_count()
    cache_hits = get_cache_hits()
    avg_latency = get_average_response_time()
    
    return AdminStatsResponse(
        total_users=db_metrics["total_users"],
        total_chats=db_metrics["total_chats"],
        uploaded_documents=db_metrics["uploaded_documents"],
        number_of_chunks=db_metrics["number_of_chunks"],
        query_count=query_count,
        cache_hits=cache_hits,
        average_response_time=round(avg_latency, 4)
    )
