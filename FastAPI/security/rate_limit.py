import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException, status

class InMemoryRateLimiter:
    def __init__(self, limit: int, window: int):
        """
        :param limit: Maximum number of allowed requests in the time window.
        :param window: Time window size in seconds.
        """
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)
        self.lock = Lock()

    def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        with self.lock:
            # Keep only requests within the active time window
            self.requests[client_ip] = [
                t for t in self.requests[client_ip]
                if now - t < self.window
            ]

            if len(self.requests[client_ip]) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )

            self.requests[client_ip].append(now)

def rate_limit(limit: int, window: int):
    """
    Generate an InMemoryRateLimiter dependency for FastAPI routes.
    Example: Depends(rate_limit(5, 60))
    """
    return InMemoryRateLimiter(limit, window)
