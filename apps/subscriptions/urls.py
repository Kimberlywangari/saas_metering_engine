from django.urls import path

from .views import MeteredEndpointView, TenantUsageStatusView, dashboardView


app_name = "subscriptions"

urlpatterns = [
    path("dashboard/", dashboardView, name="tenant-dashboard"),
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
