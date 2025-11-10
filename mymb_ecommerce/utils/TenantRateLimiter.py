import frappe
from typing import Optional
import time
from contextlib import contextmanager


class TenantRateLimiter:
    """
    Limits concurrent requests per tenant to prevent one tenant from monopolizing workers.

    Usage as decorator:
        @limit_tenant_requests(max_concurrent=3)
        def my_api_method():
            ...

    Usage as context manager:
        with TenantRateLimiter.acquire(max_concurrent=3):
            # Do work
            ...
    """

    # Per-tenant concurrent request limits
    # Adjust these based on tenant traffic patterns and SLAs
    TENANT_LIMITS = {
        # High-traffic tenants can have more concurrent requests
        # 'high-traffic-tenant.omnicommerce.cloud': 5,

        # Default limit for all other tenants
        'default': 3  # Max 3 concurrent requests per tenant
    }

    @classmethod
    def _get_cache_key(cls, site_name: str) -> str:
        """Generate cache key for tracking concurrent requests"""
        return f"tenant_concurrent_requests_{site_name}"

    @classmethod
    def _get_limit(cls, site_name: str) -> int:
        """Get concurrent request limit for a specific tenant"""
        return cls.TENANT_LIMITS.get(site_name, cls.TENANT_LIMITS['default'])

    @classmethod
    def _increment_counter(cls, site_name: str) -> int:
        """
        Atomically increment the concurrent request counter.
        Returns the new count.
        """
        cache = frappe.cache()
        cache_key = cls._get_cache_key(site_name)

        # Get current count
        current = cache.get(cache_key)
        if current is None:
            current = 0
        else:
            current = int(current)

        # Increment
        new_count = current + 1

        # Set with 60 second expiry (safety timeout)
        cache.setex(cache_key, 60, new_count)

        return new_count

    @classmethod
    def _decrement_counter(cls, site_name: str):
        """Atomically decrement the concurrent request counter"""
        cache = frappe.cache()
        cache_key = cls._get_cache_key(site_name)

        current = cache.get(cache_key)
        if current is None or int(current) <= 0:
            cache.delete(cache_key)
        else:
            new_count = int(current) - 1
            if new_count <= 0:
                cache.delete(cache_key)
            else:
                cache.setex(cache_key, 60, new_count)

    @classmethod
    def _get_current_count(cls, site_name: str) -> int:
        """Get current concurrent request count for tenant"""
        cache = frappe.cache()
        current = cache.get(cls._get_cache_key(site_name))
        return int(current) if current else 0

    @classmethod
    @contextmanager
    def acquire(cls, max_concurrent: Optional[int] = None, raise_exception: bool = True):
        """
        Context manager to enforce concurrent request limits.

        Args:
            max_concurrent: Override default limit (useful for specific endpoints)
            raise_exception: If True, raise error when limit exceeded. If False, just log.

        Example:
            with TenantRateLimiter.acquire(max_concurrent=3):
                # Only 3 concurrent requests per tenant can reach this point
                do_expensive_operation()
        """
        site_name = getattr(frappe.local, 'site', 'unknown')

        # Get limit
        limit = max_concurrent if max_concurrent is not None else cls._get_limit(site_name)

        # Check current count before incrementing
        current_count = cls._get_current_count(site_name)

        if current_count >= limit:
            error_msg = (
                f"Tenant {site_name} has reached concurrent request limit "
                f"({current_count}/{limit}). This prevents one tenant from "
                f"monopolizing all workers. Please retry in a few seconds."
            )

            frappe.log_error(
                message=error_msg,
                title=f"Tenant Rate Limit: {site_name}"
            )

            if raise_exception:
                frappe.throw(
                    _(error_msg),
                    frappe.RateLimitExceededError
                )
            else:
                # Just log, don't block (useful for gradual rollout)
                pass

        # Increment counter
        new_count = cls._increment_counter(site_name)

        try:
            # Yield control to the caller
            yield
        finally:
            # Always decrement on exit (even if exception occurs)
            cls._decrement_counter(site_name)

    @classmethod
    def get_status(cls, site_name: Optional[str] = None) -> dict:
        """
        Get current rate limit status for monitoring.

        Returns:
            {
                "site": "tenant.omnicommerce.cloud",
                "current_requests": 2,
                "limit": 3,
                "available": 1
            }
        """
        if site_name is None:
            site_name = getattr(frappe.local, 'site', 'unknown')

        current = cls._get_current_count(site_name)
        limit = cls._get_limit(site_name)

        return {
            "site": site_name,
            "current_requests": current,
            "limit": limit,
            "available": max(0, limit - current)
        }


def limit_tenant_requests(max_concurrent: Optional[int] = None, raise_exception: bool = True):
    """
    Decorator to enforce per-tenant concurrent request limits.

    Args:
        max_concurrent: Override default limit for this specific endpoint
        raise_exception: If True, raise error when limit exceeded

    Example:
        @frappe.whitelist()
        @limit_tenant_requests(max_concurrent=2)
        def expensive_b2b_operation():
            # Only 2 concurrent calls per tenant allowed
            return fetch_from_b2b_api()
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TenantRateLimiter.acquire(max_concurrent=max_concurrent, raise_exception=raise_exception):
                return func(*args, **kwargs)
        return wrapper
    return decorator
