"""Rate limiting and circuit breaker implementation."""

import asyncio
import time
import random
from typing import Dict, Any
from .logger import setup_logger

logger = setup_logger(__name__)

class RateLimiter:
    """Token bucket rate limiter with circuit breaker."""
    
    def __init__(self, rpm: int = 20, min_delay: float = 2.0, max_delay: float = 7.0, circuit_breaker_threshold: int = 3):
        self.rpm = rpm
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        
        self.interval = 60.0 / rpm if rpm > 0 else 0
        self.last_request_time = 0.0
        
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_failures = 0
        self.circuit_open = False
        self.backoff_time = 60.0  # Initial backoff time
        
    async def wait(self) -> None:
        """Wait appropriate time before next request, handling circuit breaker."""
        if self.circuit_open:
            logger.warning(f"Circuit open. Waiting for {self.backoff_time} seconds before retrying.")
            await asyncio.sleep(self.backoff_time)
            # Reset circuit to half-open state (one try allowed)
            self.circuit_open = False
            return

        now = time.time()
        time_since_last = now - self.last_request_time
        
        # Calculate base delay from rpm
        delay = max(0.0, self.interval - time_since_last)
        
        # Add random jitter between min and max delay
        jitter = random.uniform(self.min_delay, self.max_delay)
        total_delay = delay + jitter
        
        if total_delay > 0:
            logger.debug(f"Rate limiting: sleeping for {total_delay:.2f}s")
            await asyncio.sleep(total_delay)
            
        self.last_request_time = time.time()
        self.total_requests += 1
        
    def record_success(self) -> None:
        """Record a successful request and reset failure counters."""
        if self.consecutive_failures > 0:
            logger.info("Request successful, resetting circuit breaker.")
        self.consecutive_failures = 0
        self.backoff_time = 60.0  # Reset backoff time
        
    def record_failure(self) -> None:
        """Record a failure and potentially trip the circuit breaker."""
        self.consecutive_failures += 1
        self.total_failures += 1
        logger.warning(f"Request failed. Consecutive failures: {self.consecutive_failures}")
        
        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self.circuit_open = True
            self.backoff_time *= 2  # Exponential backoff
            logger.error(f"Circuit breaker tripped! Next backoff: {self.backoff_time}s")
            
    def is_circuit_open(self) -> bool:
        """Check if the circuit is currently open."""
        return self.circuit_open
        
    def reset(self) -> None:
        """Reset the rate limiter state completely."""
        self.last_request_time = 0.0
        self.consecutive_failures = 0
        self.circuit_open = False
        self.backoff_time = 60.0
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics of the rate limiter."""
        return {
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "circuit_open": self.circuit_open,
            "current_backoff": self.backoff_time
        }
