from django.urls import path

from .views import MeteredEndpointView, TenantUsageStatusView

app_name = "subscriptions"

urlpatterns = [
    path("meter/", MeteredEndpointView.as_view(), name="metered-endpoint"),
    path(
        "tenants/<int:tenant_id>/usage/",
        TenantUsageStatusView.as_view(),
        name="tenant-usage-status",
    ),
    path(
        "tenants/usage/",
        TenantUsageStatusView.as_view(),
        name="tenant-usage-status-header",
    ),
]
