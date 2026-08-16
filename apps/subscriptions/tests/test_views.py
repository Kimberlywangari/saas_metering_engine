import json
from decimal import Decimal

from django.test import Client, TestCase

from apps.subscriptions.models import SubscriptionTier, TenantAccount


class MeteredEndpointViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tier = SubscriptionTier.objects.create(
            name="BASIC",
            monthly_price=Decimal("9.99"),
            api_call_limit=3,
        )
        self.tenant = TenantAccount.objects.create(
            company_name="Acme Corp",
            billing_email="billing@acme.example",
            tier=self.tier,
        )
        self.url = "/api/meter/"

    def test_returns_200_with_valid_header_and_available_quota(self):
        response = self.client.get(
            self.url, HTTP_X_TENANT_ID=str(self.tenant.id)
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload["allowed"])
        self.assertEqual(payload["remaining_calls"], 2)

    def test_post_method_also_meters_the_call(self):
        response = self.client.post(
            self.url, HTTP_X_TENANT_ID=str(self.tenant.id)
        )
        self.assertEqual(response.status_code, 200)

        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.current_api_usage, 1)

    def test_returns_429_when_quota_is_hit(self):
        self.tenant.current_api_usage = 3
        self.tenant.save(update_fields=["current_api_usage"])

        response = self.client.get(
            self.url, HTTP_X_TENANT_ID=str(self.tenant.id)
        )

        self.assertEqual(response.status_code, 429)
        payload = json.loads(response.content)
        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["reason"], "Daily API quota exceeded")

    def test_returns_403_when_account_past_due(self):
        self.tenant.status = TenantAccount.STATUS_PAST_DUE
        self.tenant.save(update_fields=["status"])

        response = self.client.get(
            self.url, HTTP_X_TENANT_ID=str(self.tenant.id)
        )

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertFalse(payload["allowed"])

    def test_returns_400_when_tenant_id_header_missing(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 400)
        payload = json.loads(response.content)
        self.assertIn("error", payload)

    def test_returns_400_when_tenant_id_header_not_an_integer(self):
        response = self.client.get(self.url, HTTP_X_TENANT_ID="not-an-int")

        self.assertEqual(response.status_code, 400)

    def test_returns_404_for_unknown_tenant_id(self):
        response = self.client.get(self.url, HTTP_X_TENANT_ID="999999")

        self.assertEqual(response.status_code, 404)


class TenantUsageStatusViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tier = SubscriptionTier.objects.create(
            name="PRO",
            monthly_price=Decimal("49.99"),
            api_call_limit=200,
        )
        self.tenant = TenantAccount.objects.create(
            company_name="Beta LLC",
            billing_email="billing@beta.example",
            tier=self.tier,
            current_api_usage=50,
        )

    def test_outputs_correct_json_metrics_via_url_parameter(self):
        response = self.client.get(f"/api/tenants/{self.tenant.id}/usage/")

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["company_name"], "Beta LLC")
        self.assertEqual(payload["tier_name"], "PRO")
        self.assertEqual(payload["daily_quota"], 200)
        self.assertEqual(payload["current_usage"], 50)
        self.assertEqual(payload["percentage_consumed"], 25.0)
        self.assertEqual(payload["status"], "ACTIVE")

    def test_outputs_correct_json_metrics_via_header(self):
        response = self.client.get(
            "/api/tenants/usage/", HTTP_X_TENANT_ID=str(self.tenant.id)
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["company_name"], "Beta LLC")

    def test_returns_400_when_no_tenant_identifier_supplied(self):
        response = self.client.get("/api/tenants/usage/")
        self.assertEqual(response.status_code, 400)

    def test_returns_404_for_unknown_tenant(self):
        response = self.client.get("/api/tenants/999999/usage/")
        self.assertEqual(response.status_code, 404)