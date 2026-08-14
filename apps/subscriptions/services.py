"""
Service-layer functions for the subscriptions app.

These functions contain the business logic for API metering and account
state transitions. They are kept free of any HTTP/request concerns so they
can be unit tested directly and reused from views, management commands, or
background tasks.
"""

from django.db.models import F

from .models import TenantAccount


def record_api_call(tenant_id: int) -> dict:
    """
    Record a single metered API call for the given tenant.

    Returns a dict describing whether the call is allowed and, if not, why.
    The `current_api_usage` counter is incremented atomically at the
    database level using an F() expression so concurrent requests for the
    same tenant cannot race each other and undercount usage.
    """
    tenant = TenantAccount.objects.select_related("tier").get(pk=tenant_id)

    if not tenant.is_operational():
        return {
            "allowed": False,
            "reason": "Account is inactive or past due",
            "status_code": 403,
        }

    if tenant.has_exceeded_quota():
        return {
            "allowed": False,
            "reason": "Daily API quota exceeded",
            "status_code": 429,
        }

    TenantAccount.objects.filter(pk=tenant_id).update(
        current_api_usage=F("current_api_usage") + 1
    )

    tenant.refresh_from_db(fields=["current_api_usage"])
    remaining_calls = tenant.tier.api_call_limit - tenant.current_api_usage

    return {
        "allowed": True,
        "remaining_calls": max(remaining_calls, 0),
        "status_code": 200,
    }


def reset_daily_usage() -> int:
    
    return TenantAccount.objects.update(current_api_usage=0)


def update_tenant_status(tenant_id: int, new_status: str) -> TenantAccount:
    
    valid_statuses = {choice for choice, _ in TenantAccount.STATUS_CHOICES}
    if new_status not in valid_statuses:
        raise ValueError(
            f"'{new_status}' is not a valid status. "
            f"Expected one of: {sorted(valid_statuses)}"
        )

    tenant = TenantAccount.objects.get(pk=tenant_id)
    tenant.status = new_status
    tenant.save(update_fields=["status", "updated_at"])
    return tenant
