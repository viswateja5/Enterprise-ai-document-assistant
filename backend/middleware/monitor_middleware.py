import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

# Local imports
from monitoring.metrics import REQUEST_COUNT, REQUEST_LATENCY, record_response_time

class MonitorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that records HTTP latency metrics, counts total requests,
    and updates performance histograms.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Avoid recording metrics on scrapable /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
            
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception:
            status_code = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time
            
            # Exclude query streaming loops or other non-query APIs from average RAG response stats
            # only track standard endpoints like /query or /upload in RAG mean responses
            if "/query" in request.url.path or "/upload" in request.url.path:
                record_response_time(duration)
                
            # Update Prometheus metrics
            REQUEST_COUNT.labels(
                method=request.method, 
                endpoint=request.url.path, 
                status=status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method, 
                endpoint=request.url.path
            ).observe(duration)
