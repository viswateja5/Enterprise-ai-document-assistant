from prometheus_client import Counter, Histogram, Gauge

# Prometheus Counters
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total count of incoming HTTP requests.", 
    ["method", "endpoint", "status"]
)

# Prometheus Histogram to measure request latencies
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", 
    "Request processing latency in seconds.", 
    ["method", "endpoint"]
)

# Prometheus Gauge to monitor active session counts
ACTIVE_USERS = Gauge(
    "active_users_gauge", 
    "Number of active user accounts."
)

# Custom performance metrics list for admin analytics dashboard stats (stored in-memory)
latencies_history = []

def record_response_time(seconds: float) -> None:
    """
    Appends a new query duration sample, keeping historical entries capped at 500.
    """
    latencies_history.append(seconds)
    if len(latencies_history) > 500:
        latencies_history.pop(0)

def get_average_response_time() -> float:
    """
    Calculates the mean query latency duration in seconds.
    """
    if not latencies_history:
        return 0.0
    return sum(latencies_history) / len(latencies_history)
