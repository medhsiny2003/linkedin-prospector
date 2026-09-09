import time
import random
import asyncio
import logging

from .circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate Limiter with human-like jitter, exponential backoff, and Circuit Breaker integration.
    """
    def __init__(self, rpm: int = 20, jitter_min: float = 5.0, jitter_max: float = 15.0):
        """
        Initializes the Rate Limiter.
        
        Args:
            rpm: Requests per minute limit.
            jitter_min: Minimum random delay between requests in seconds.
            jitter_max: Maximum random delay between requests in seconds.
        """
        self.rpm = rpm
        self.jitter_min = jitter_min
        self.jitter_max = jitter_max
        self.min_interval = 60.0 / rpm if rpm > 0 else 0.0
        self.last_request_time = 0.0
        self.circuit_breaker = CircuitBreaker()
        self.consecutive_errors = 0

    async def wait(self) -> None:
        """
        Wait for the appropriate amount of time before the next request.
        Integrates RPM limits, human jitter, exponential backoff, and circuit breaker.
        """
        # Wait if circuit breaker is OPEN
        while not self.circuit_breaker.allow_request():
            logger.warning("RateLimiter: Circuit breaker is OPEN. Waiting for reset...")
            await asyncio.sleep(10)

        now = time.time()
        time_since_last = now - self.last_request_time
        
        # Calculate human jitter delay
        jitter = random.uniform(self.jitter_min, self.jitter_max)
        
        # Calculate delay based on RPM
        required_delay = max(0.0, self.min_interval - time_since_last)
        
        # Exponential backoff based on recent transient errors
        backoff = 0.0
        if self.consecutive_errors > 0:
            backoff = (2 ** min(self.consecutive_errors, 6)) + random.uniform(0, 1)
            
        total_delay = max(required_delay, jitter) + backoff
        
        if total_delay > 0:
            logger.debug(f"RateLimiter: Waiting for {total_delay:.2f} seconds...")
            await asyncio.sleep(total_delay)
            
        self.last_request_time = time.time()

    def record_success(self) -> None:
        """Record a successful request."""
        self.consecutive_errors = 0
        self.circuit_breaker.record_success()

    def record_failure(self) -> None:
        """Record a failed request (e.g., rate limit, network error)."""
        self.consecutive_errors += 1
        self.circuit_breaker.record_failure()
