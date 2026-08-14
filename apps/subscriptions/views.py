
# Create your views here.
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import TenantAccount
from .services import record_api_call

TENANT_ID_HEADER = "HTTP_X_TENANT_ID"


@method_decorator(csrf_exempt, name="dispatch")
class MeteredEndpointView(View):
   
    def get(self, request, *args, **kwargs):
        return self._handle(request)

    def post(self, request, *args, **kwargs):
        return self._handle(request)

    def _handle(self, request):
        tenant_id = request.META.get(TENANT_ID_HEADER)
        if not tenant_id:
            return JsonResponse(
                {"error": "X-Tenant-ID header is required"}, status=400
            )

        try:
            tenant_id = int(tenant_id)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "X-Tenant-ID header must be a valid integer"},
                status=400,
            )

        try:
            result = record_api_call(tenant_id)
        except TenantAccount.DoesNotExist:
            return JsonResponse(
                {"error": f"No tenant found with id={tenant_id}"}, status=404
            )

        status_code = result.pop("status_code")
        return JsonResponse(result, status=status_code)


class TenantUsageStatusView(View):
    """
    Read-only view returning a tenant's current usage snapshot: company
    name, tier name, daily quota, usage count, and percentage consumed.
    """

    def get(self, request, tenant_id=None, *args, **kwargs):
        if tenant_id is None:
            tenant_id = request.META.get(TENANT_ID_HEADER)

        if not tenant_id:
            return JsonResponse(
                {"error": "tenant_id is required (as a URL parameter or "
                          "X-Tenant-ID header)"},
                status=400,
            )

        try:
            tenant_id = int(tenant_id)
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "tenant_id must be a valid integer"}, status=400
            )

        try:
            tenant = TenantAccount.objects.select_related("tier").get(
                pk=tenant_id
            )
        except TenantAccount.DoesNotExist:
            return JsonResponse(
                {"error": f"No tenant found with id={tenant_id}"}, status=404
            )

        quota = tenant.tier.api_call_limit
        usage = tenant.current_api_usage
        percentage_consumed = round((usage / quota) * 100, 2) if quota else 0.0

        return JsonResponse(
            {
                "company_name": tenant.company_name,
                "tier_name": tenant.tier.name,
                "daily_quota": quota,
                "current_usage": usage,
                "percentage_consumed": percentage_consumed,
                "status": tenant.status,
            },
            status=200,
        )
