import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Local imports
from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limit import limiter
from app.services.rag_service import init_redis
from app.api.auth import auth_router
from app.api.upload import upload_router
from app.api.query import query_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rag-backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Asynchronous startup and shutdown event lifespan contexts.
    """
    logger.info("Starting up Enterprise RAG Chatbot application...")
    
    # 1. Initialize SQLite Database tables
    logger.info("Initializing database tables...")
    await init_db()
    
    # 2. Connect to Redis Cache (falls back to local memory if offline)
    logger.info("Initializing Redis connections...")
    await init_redis()
    
    yield
    
    logger.info("Shutting down Enterprise RAG Chatbot application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade Document Search Assistant (RAG) Backend API service.",
    version="2.0.0",
    lifespan=lifespan
)

# Set up slowapi Limiter state on FastAPI
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust allowed domains list for security in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for rate limiting to return consistent JSON detail
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded by IP: {request.client.host}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please retry in a moment."}
    )

# Register sub-routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(query_router)

@app.get("/")
async def root():
    """
    System status checker metadata route.
    """
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_version": "2.0.0",
        "supported_formats": ["PDF", "DOCX", "TXT"]
    }
