import time
import frappe
from typing import Callable, Any, Optional
from datetime import datetime


class CircuitBreaker:
    """
    Circuit Breaker pattern to prevent cascading failures from slow/failing external services.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately (fail fast)
    - HALF_OPEN: Testing if service recovered, allow limited requests
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3
    ):
        """
        Args:
            name: Unique identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before trying again (OPEN -> HALF_OPEN)
            half_open_max_calls: Max calls allowed in HALF_OPEN state before deciding
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls

    def _get_cache_key(self, suffix: str) -> str:
        """Generate cache key for circuit breaker state"""
        return f"circuit_breaker_{self.name}_{suffix}"

    def _get_state(self) -> str:
        """Get current circuit state from cache"""
        cache = frappe.cache()
        return cache.get(self._get_cache_key("state")) or "CLOSED"

    def _set_state(self, state: str):
        """Set circuit state in cache"""
        cache = frappe.cache()
        cache.setex(self._get_cache_key("state"), self.timeout_seconds * 2, state)

    def _get_failure_count(self) -> int:
        """Get current failure count"""
        cache = frappe.cache()
        return int(cache.get(self._get_cache_key("failures")) or 0)

    def _increment_failures(self):
        """Increment failure counter"""
        cache = frappe.cache()
        count = self._get_failure_count() + 1
        cache.setex(self._get_cache_key("failures"), self.timeout_seconds * 2, count)
        return count

    def _reset_failures(self):
        """Reset failure counter"""
        cache = frappe.cache()
        cache.delete(self._get_cache_key("failures"))

    def _get_last_failure_time(self) -> Optional[float]:
        """Get timestamp of last failure"""
        cache = frappe.cache()
        timestamp = cache.get(self._get_cache_key("last_failure"))
        return float(timestamp) if timestamp else None

    def _set_last_failure_time(self):
        """Record timestamp of failure"""
        cache = frappe.cache()
        cache.setex(self._get_cache_key("last_failure"), self.timeout_seconds * 2, time.time())

    def _get_half_open_calls(self) -> int:
        """Get number of calls made in HALF_OPEN state"""
        cache = frappe.cache()
        return int(cache.get(self._get_cache_key("half_open_calls")) or 0)

    def _increment_half_open_calls(self):
        """Increment HALF_OPEN call counter"""
        cache = frappe.cache()
        count = self._get_half_open_calls() + 1
        cache.setex(self._get_cache_key("half_open_calls"), 60, count)
        return count

    def _reset_half_open_calls(self):
        """Reset HALF_OPEN call counter"""
        cache = frappe.cache()
        cache.delete(self._get_cache_key("half_open_calls"))

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Raises:
            Exception: If circuit is OPEN (service is down)
            Original exception: If function fails
        """
        state = self._get_state()

        # OPEN state: Reject immediately, check if timeout expired
        if state == "OPEN":
            last_failure = self._get_last_failure_time()
            if last_failure and (time.time() - last_failure) >= self.timeout_seconds:
                # Timeout expired, try HALF_OPEN
                self._set_state("HALF_OPEN")
                self._reset_half_open_calls()
                frappe.log_error(
                    message=f"Circuit breaker {self.name} transitioning to HALF_OPEN",
                    title=f"Circuit Breaker: {self.name}"
                )
            else:
                # Still in timeout, fail fast
                error_msg = f"Circuit breaker OPEN for {self.name}. Service unavailable, failing fast to prevent worker blocking."
                frappe.log_error(
                    message=f"{error_msg} (will retry after {self.timeout_seconds}s)",
                    title=f"Circuit Breaker OPEN: {self.name}"
                )
                raise Exception(error_msg)

        # HALF_OPEN state: Limited testing
        if state == "HALF_OPEN":
            calls_made = self._get_half_open_calls()
            if calls_made >= self.half_open_max_calls:
                # Too many test calls, back to OPEN
                self._set_state("OPEN")
                raise Exception(f"Circuit breaker {self.name} still failing, back to OPEN state")

            self._increment_half_open_calls()

        # Try the actual call
        try:
            result = func(*args, **kwargs)

            # Success! Reset everything
            if state in ["HALF_OPEN", "OPEN"]:
                frappe.log_error(
                    message=f"Circuit breaker {self.name} recovered, transitioning to CLOSED",
                    title=f"Circuit Breaker Recovered: {self.name}"
                )

            self._reset_failures()
            self._reset_half_open_calls()
            self._set_state("CLOSED")

            return result

        except Exception as e:
            # Failure occurred
            failure_count = self._increment_failures()
            self._set_last_failure_time()

            # Check if we should open the circuit
            if failure_count >= self.failure_threshold:
                self._set_state("OPEN")
                frappe.log_error(
                    message=f"Circuit breaker {self.name} OPENED after {failure_count} failures. Error: {str(e)}",
                    title=f"Circuit Breaker OPENED: {self.name}"
                )
            else:
                frappe.log_error(
                    message=f"Circuit breaker {self.name} failure {failure_count}/{self.failure_threshold}. Error: {str(e)}",
                    title=f"Circuit Breaker Failure: {self.name}"
                )

            # Re-raise the original exception
            raise

    def get_status(self) -> dict:
        """Get current circuit breaker status for monitoring"""
        return {
            "name": self.name,
            "state": self._get_state(),
            "failure_count": self._get_failure_count(),
            "last_failure_time": self._get_last_failure_time(),
            "half_open_calls": self._get_half_open_calls()
        }

    def reset(self):
        """Manually reset circuit breaker (for admin use)"""
        self._reset_failures()
        self._reset_half_open_calls()
        self._set_state("CLOSED")
        frappe.log_error(
            message=f"Circuit breaker {self.name} manually reset to CLOSED",
            title=f"Circuit Breaker Reset: {self.name}"
        )
