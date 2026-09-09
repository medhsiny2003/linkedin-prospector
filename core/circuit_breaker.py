import time
import logging
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.
    Prevents repeated execution of operations that are likely to fail.
    
    States:
    - CLOSED: Normal operation. Requests are allowed.
    - OPEN: Tripped state. Requests are blocked until reset timeout.
    - HALF_OPEN: Probing state. One request is allowed to test the system.
    """
    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_failure(self) -> None:
        """Records a failure and potentially trips the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(f"CircuitBreaker: Failure recorded. Count: {self.failure_count}/{self.failure_threshold}")
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self._trip()
        elif self.state == CircuitState.HALF_OPEN:
            self._trip()

    def record_success(self) -> None:
        """Records a success and resets the circuit breaker."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("CircuitBreaker: Success during HALF_OPEN. Resetting to CLOSED.")
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _trip(self) -> None:
        """Trips the circuit breaker to the OPEN state."""
        logger.error("CircuitBreaker: Threshold reached. Tripping circuit to OPEN.")
        self.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """
        Checks if a request should be allowed based on the current state.
        
        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            time_since_failure = time.time() - self.last_failure_time
            if time_since_failure >= self.reset_timeout:
                logger.info("CircuitBreaker: Reset timeout passed. Transitioning to HALF_OPEN.")
                self.state = CircuitState.HALF_OPEN
                return True
            return False
            
        if self.state == CircuitState.HALF_OPEN:
            return True
            
        return False
