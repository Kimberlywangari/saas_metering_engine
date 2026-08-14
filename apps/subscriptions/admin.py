from django.contrib import admin

# Register your models here.
from decimal import Decimal

from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import SubscriptionTier, TenantAccount

STATUS_BADGE_COLORS = {
    TenantAccount.STATUS_ACTIVE: "#1a7f37",
    TenantAccount.STATUS_PAST_DUE: "#b35900",
    TenantAccount.STATUS_CANCELED: "#b91c1c",
}


@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ("name", "monthly_price", "api_call_limit", "tenant_count")
    search_fields = ("name",)
    ordering = ("monthly_price",)

    @admin.display(description="Active Tenants")
    def tenant_count(self, tier: SubscriptionTier) -> int:
        return tier.tenants.count()


@admin.register(TenantAccount)
class TenantAccountAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "tier_name",
        "usage_ratio",
        "status_badge",
    )
    list_filter = ("status", "tier")
    search_fields = ("company_name", "billing_email")
    ordering = ("company_name",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Tier", ordering="tier__name")
    def tier_name(self, tenant: TenantAccount) -> str:
        return tenant.tier.name

    @admin.display(description="Usage / Quota")
    def usage_ratio(self, tenant: TenantAccount) -> str:
        return f"{tenant.current_api_usage} / {tenant.tier.api_call_limit}"

    @admin.display(description="Status")
    def status_badge(self, tenant: TenantAccount):
        color = STATUS_BADGE_COLORS.get(tenant.status, "#6b7280")
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;'
            'border-radius:10px;color:#fff;background-color:{};">{}</span>',
            color,
            tenant.get_status_display(),
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["mrr_summary"] = self._compute_mrr_summary()
        return super().changelist_view(request, extra_context=extra_context)

    def _compute_mrr_summary(self) -> Decimal:
        """
        Aggregate Monthly Recurring Revenue across every ACTIVE tenant.

        Uses Decimal-based aggregation (Sum on a DecimalField) rather than
        summing in Python so the result never picks up binary
        floating-point rounding error.
        """
        active_tenants = TenantAccount.objects.filter(
            status=TenantAccount.STATUS_ACTIVE
        ).select_related("tier")
        total = active_tenants.aggregate(mrr=Sum("tier__monthly_price"))["mrr"]
        total = total or Decimal("0.00")
        # SQLite has no native DECIMAL type, so Django emulates DecimalField
        # aggregation through a float-backed intermediate representation,
        # which can surface trailing floating-point noise (e.g.
        # 49.9900000000000). Quantizing back to 2 decimal places restores a
        # clean currency value regardless of backend.
        return Decimal(total).quantize(Decimal("0.01"))
