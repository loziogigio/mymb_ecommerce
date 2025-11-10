"""
Request hooks for tenant isolation and rate limiting.
"""

import frappe
from mymb_ecommerce.utils.TenantRateLimiter import TenantRateLimiter


def apply_tenant_rate_limit():
    """
    Frappe hook: app_include_js or on_session_creation

    Apply per-tenant concurrent request limiting to prevent one tenant
    from monopolizing all gunicorn workers.

    To enable, add to hooks.py:
        before_request = [
            "mymb_ecommerce.utils.request_hooks.apply_tenant_rate_limit"
        ]
    """
    # Skip rate limiting for certain paths
    skip_paths = [
        '/api/method/ping',
        '/assets/',
        '/files/',
        '/private/files/',
        '/desk',
        '/app',
    ]

    request_path = frappe.request.path if hasattr(frappe, 'request') else ''

    # Skip static assets and desk
    for skip_path in skip_paths:
        if request_path.startswith(skip_path):
            return

    # Apply rate limiting
    try:
        # Store in frappe.local so we can release it in after_request
        frappe.local.rate_limiter_context = TenantRateLimiter.acquire(raise_exception=True)
        frappe.local.rate_limiter_context.__enter__()
    except frappe.RateLimitExceededError:
        # Let it bubble up - Frappe will handle it
        raise
    except Exception as e:
        # Log but don't break requests
        frappe.log_error(
            message=f"Failed to apply rate limiting: {str(e)}",
            title="Rate Limiter Error"
        )


def release_tenant_rate_limit():
    """
    Frappe hook: after_request

    Release the rate limit counter after request completes.

    To enable, add to hooks.py:
        after_request = [
            "mymb_ecommerce.utils.request_hooks.release_tenant_rate_limit"
        ]
    """
    if hasattr(frappe.local, 'rate_limiter_context'):
        try:
            frappe.local.rate_limiter_context.__exit__(None, None, None)
        except Exception as e:
            frappe.log_error(
                message=f"Failed to release rate limiting: {str(e)}",
                title="Rate Limiter Error"
            )


@frappe.whitelist(allow_guest=True)
def get_tenant_rate_limit_status():
    """
    API endpoint to check current rate limit status.

    Usage:
        GET /api/method/mymb_ecommerce.utils.request_hooks.get_tenant_rate_limit_status

    Returns:
        {
            "site": "tenant.omnicommerce.cloud",
            "current_requests": 2,
            "limit": 3,
            "available": 1
        }
    """
    return TenantRateLimiter.get_status()
