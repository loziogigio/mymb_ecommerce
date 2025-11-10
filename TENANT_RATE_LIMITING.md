# Per-Tenant Request Rate Limiting

## Problem

With 10 tenants sharing 8-10 gunicorn workers, one tenant's high traffic or slow operations can monopolize all workers, causing slowness for other tenants.

**Example:**
- Tenant A makes 6 concurrent slow B2B API calls (30s each)
- 6 of 8 workers are now busy for 30 seconds
- Only 2 workers remain for the other 9 tenants
- Result: All tenants experience slowness

## Solution

Limit how many **concurrent requests** each tenant can have at once:

- Each tenant limited to **3 concurrent requests** by default
- If limit exceeded, request fails immediately with `429 Too Many Requests`
- Workers remain available for other tenants
- Fair distribution of resources across all tenants

## How It Works

```
10 Tenants, 8 Workers, Limit = 3 concurrent per tenant

Tenant A: Makes 10 requests
  → First 3 requests proceed (use 3 workers)
  → Requests 4-10 get rejected: "Rate limit exceeded"
  → Only uses 3 workers max

Remaining 5 workers available for Tenants B-J ✅
```

## Installation

### Step 1: Enable Request Hooks

Edit `/workspace/development/frappe-bench/apps/mymb_ecommerce/mymb_ecommerce/hooks.py`:

```python
# Add these lines to hooks.py

# Request Hooks - Tenant Rate Limiting
# -------------------------------------
before_request = [
    "mymb_ecommerce.utils.request_hooks.apply_tenant_rate_limit"
]

after_request = [
    "mymb_ecommerce.utils.request_hooks.release_tenant_rate_limit"
]
```

### Step 2: Restart Backend

```bash
# Restart to apply hooks
docker restart erpnext-omnicommerce-backend-1

# Or if using bench directly
bench restart
```

### Step 3: Monitor (Optional)

Check current rate limit status:

```bash
# Via API
curl http://your-site.omnicommerce.cloud/api/method/mymb_ecommerce.utils.request_hooks.get_tenant_rate_limit_status

# Response:
{
  "site": "tenant.omnicommerce.cloud",
  "current_requests": 2,
  "limit": 3,
  "available": 1
}
```

## Configuration

### Adjust Global Default

Edit `/workspace/development/frappe-bench/apps/mymb_ecommerce/mymb_ecommerce/utils/TenantRateLimiter.py`:

```python
class TenantRateLimiter:
    TENANT_LIMITS = {
        # Default for all tenants
        'default': 3  # Change this number
    }
```

### Per-Tenant Limits

For high-traffic tenants that need more concurrent requests:

```python
class TenantRateLimiter:
    TENANT_LIMITS = {
        # High-traffic tenant with premium SLA
        'premium-tenant.omnicommerce.cloud': 5,

        # Default for everyone else
        'default': 3
    }
```

### Per-Endpoint Limits

For specific endpoints that need different limits:

```python
from mymb_ecommerce.utils.TenantRateLimiter import limit_tenant_requests

@frappe.whitelist()
@limit_tenant_requests(max_concurrent=1)  # Override: only 1 concurrent
def very_expensive_operation():
    """This endpoint can only have 1 concurrent request per tenant"""
    return fetch_from_slow_b2b_api()

@frappe.whitelist()
@limit_tenant_requests(max_concurrent=5)  # Override: allow 5 concurrent
def fast_cached_operation():
    """This endpoint can have 5 concurrent requests per tenant"""
    return get_from_cache()
```

## Expected Impact

### Before Rate Limiting:

| Scenario | Workers Used | Other Tenants Impact |
|----------|--------------|---------------------|
| Tenant A: 6 concurrent requests | 6 of 8 | ⚠️ Only 2 workers left |
| Tenant A: 10 concurrent requests | 8 of 8 | ❌ All workers blocked |

### After Rate Limiting:

| Scenario | Workers Used | Other Tenants Impact |
|----------|--------------|---------------------|
| Tenant A: 6 concurrent requests | 3 of 8 (limit) | ✅ 5 workers available |
| Tenant A: 10 concurrent requests | 3 of 8 (limit) | ✅ 5 workers available |

## Error Handling

When a tenant exceeds their limit, they receive:

**HTTP 429 - Too Many Requests**

```json
{
  "exc_type": "RateLimitExceededError",
  "message": "Tenant tenant.omnicommerce.cloud has reached concurrent request limit (3/3). Please retry in a few seconds."
}
```

Client should implement **exponential backoff retry**:
- Wait 1 second, retry
- If fails, wait 2 seconds, retry
- If fails, wait 4 seconds, retry
- etc.

## Monitoring

### Check Logs

Frappe Error Log will show rate limit events:

```
Title: Tenant Rate Limit: tenant.omnicommerce.cloud
Message: Tenant has reached concurrent request limit (3/3)
```

### Metrics to Track

1. **Rate limit errors per tenant** - Which tenants hit limits most?
2. **Current concurrent requests** - Use the API endpoint
3. **Worker utilization** - Are workers more evenly distributed now?

## Gradual Rollout (Optional)

To test without blocking requests initially:

```python
# In request_hooks.py, change this line:
frappe.local.rate_limiter_context = TenantRateLimiter.acquire(raise_exception=False)
```

This will:
- ✅ Log when limits are exceeded
- ✅ Track metrics
- ❌ NOT reject requests (just warn)

Once validated, change back to `raise_exception=True`.

## Troubleshooting

### Issue: Legitimate traffic getting blocked

**Solution:** Increase limit for that tenant

```python
TENANT_LIMITS = {
    'high-traffic-tenant.omnicommerce.cloud': 5,  # Increased from 3
    'default': 3
}
```

### Issue: Still seeing worker monopolization

**Possible causes:**
1. Limit too high - Reduce default from 3 to 2
2. One endpoint very slow - Add per-endpoint limit (see above)
3. Need more workers - Increase gunicorn worker count

### Issue: Rate limit counter stuck

The counter has a 60-second safety timeout. If stuck:

```python
# Clear rate limit for a tenant
import frappe
cache = frappe.cache()
cache.delete("tenant_concurrent_requests_tenant.omnicommerce.cloud")
```

## Complete Tenant Isolation Stack

This rate limiter works together with other protections:

1. ✅ **Circuit Breakers** - Fail fast when external services down
2. ✅ **Database Timeouts** - 3s connection, 30s query timeout
3. ✅ **Lock Timeouts** - 3s wait for table locks
4. ✅ **API Timeouts** - 3s connection, 30s read timeout
5. ✅ **Connection Pools** - Max 3+5 DB connections per tenant
6. ✅ **Request Rate Limiting** - Max 3 concurrent requests per tenant (this file)

Together these provide **complete multi-tenant isolation**.
