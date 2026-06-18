import os
import json
import logging
from typing import Optional, Any, Dict
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
logger = logging.getLogger("rag-backend")

redis_client: Optional[aioredis.Redis] = None
local_cache: Dict[str, Any] = {}

# In-memory counter tracking cache hits for admin analytics stats
cache_hits_count: int = 0

async def init_redis() -> bool:
    """
    Initializes the connection to Redis. 
    
    Returns:
        bool: True if connection is online, False if fallback required.
    """
    global redis_client
    try:
        redis_client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=2.0
        )
        await redis_client.ping()
        logger.info("Connected to Redis cache successfully.")
        return True
    except Exception as e:
        logger.warning(
            f"Failed to connect to Redis. Caching will use local memory fallback: {str(e)}"
        )
        redis_client = None
        return False

async def get_cached(key: str) -> Optional[Any]:
    """
    Retrieves a cached value. Tracks hits for admin statistics.
    """
    global cache_hits_count
    
    # 1. Try Redis cache
    if redis_client:
        try:
            val = await redis_client.get(key)
            if val:
                cache_hits_count += 1
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis cache retrieve failed: {str(e)}")
            
    # 2. Try In-memory fallback dictionary
    if key in local_cache:
        cache_hits_count += 1
        return local_cache[key]
        
    return None

async def set_cached(key: str, data: Any, expire_seconds: int = 3600) -> None:
    """
    Caches a value with expiration settings.
    """
    # 1. Set inside Redis cache
    if redis_client:
        try:
            await redis_client.setex(key, expire_seconds, json.dumps(data))
            return
        except Exception as e:
            logger.warning(f"Redis cache write failed: {str(e)}")
            
    # 2. Set inside In-memory fallback dictionary
    local_cache[key] = data

def get_cache_hits() -> int:
    """
    Returns the total count of successfully resolved cache requests.
    """
    return cache_hits_count
