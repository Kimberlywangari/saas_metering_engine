from decimal import Decimal

from django.test import TestCase

from apps.subscriptions.models import SubscriptionTier, TenantAccount
from apps.subscriptions.services import (
    record_api_call,
    reset_daily_usage,
    update_tenant_status,
)


class RecordApiCallTests(TestCase):
    def setUp(self):
        self.tier = SubscriptionTier.objects.create(
            name="BASIC",
            monthly_price=Decimal("9.99"),
            api_call_limit=5,
        )
        self.tenant = TenantAccount.objects.create(
            company_name="Acme Corp",
            billing_email="billing@acme.example",
            tier=self.tier,
        )

    def test_allows_request_under_quota_and_increments_counter(self):
        result = record_api_call(self.tenant.id)

        self.assertTrue(result["allowed"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["remaining_calls"], 4)

        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.current_api_usage, 1)

    def test_multiple_calls_increment_counter_sequentially(self):
        for expected_usage in range(1, 4):
            record_api_call(self.tenant.id)
            self.tenant.refresh_from_db()
            self.assertEqual(self.tenant.current_api_usage, expected_usage)

    def test_blocks_request_when_usage_equals_quota(self):
        self.tenant.current_api_usage = 5
        self.tenant.save(update_fields=["current_api_usage"])

        result = record_api_call(self.tenant.id)

        self.assertFalse(result["allowed"])
        self.assertEqual(result["status_code"], 429)
        self.assertEqual(result["reason"], "Daily API quota exceeded")

        # Usage must not have been incremented past the quota.
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.current_api_usage, 5)

    def test_blocks_request_when_usage_exceeds_quota(self):
        self.tenant.current_api_usage = 7
        self.tenant.save(update_fields=["current_api_usage"])

        result = record_api_call(self.tenant.id)

        self.assertFalse(result["allowed"])
        self.assertEqual(result["status_code"], 429)

    def test_blocks_request_when_status_is_past_due(self):
        self.tenant.status = TenantAccount.STATUS_PAST_DUE
        self.tenant.save(update_fields=["status"])

        result = record_api_call(self.tenant.id)

        self.assertFalse(result["allowed"])
        self.assertEqual(result["status_code"], 403)
        self.assertEqual(
            result["reason"], "Account is inactive or past due"
        )

    def test_blocks_request_when_status_is_canceled(self):
        self.tenant.status = TenantAccount.STATUS_CANCELED
        self.tenant.save(update_fields=["status"])

        result = record_api_call(self.tenant.id)

        self.assertFalse(result["allowed"])
        self.assertEqual(result["status_code"], 403)

    def test_inactive_status_checked_before_quota(self):
        # Even if quota is also exceeded, the inactive-account reason
        # should take precedence, matching the documented check order.
        self.tenant.status = TenantAccount.STATUS_CANCELED
        self.tenant.current_api_usage = 100
        self.tenant.save(update_fields=["status", "current_api_usage"])

        result = record_api_call(self.tenant.id)

        self.assertEqual(result["status_code"], 403)

    def test_raises_does_not_exist_for_unknown_tenant(self):
        with self.assertRaises(TenantAccount.DoesNotExist):
            record_api_call(tenant_id=999999)

    def test_concurrent_style_updates_use_f_expression_atomically(self):
        """
        Simulate two "concurrent" calls by fetching two independent Python
        model instances for the same row and issuing record_api_call for
        each. Because the underlying increment uses F('current_api_usage')
        + 1 at the database level (not a read-modify-write in Python), both
        calls should be reflected -- there is no lost update.
        """
        tenant_copy_a = TenantAccount.objects.get(pk=self.tenant.id)
        tenant_copy_b = TenantAccount.objects.get(pk=self.tenant.id)

        # Both copies currently believe usage is 0 in memory.
        self.assertEqual(tenant_copy_a.current_api_usage, 0)
        self.assertEqual(tenant_copy_b.current_api_usage, 0)

        record_api_call(tenant_copy_a.id)
        record_api_call(tenant_copy_b.id)

        self.tenant.refresh_from_db()
        # If the increment had been a Python-side read-modify-write using
        # the stale in-memory instances, this would incorrectly be 1
        # instead of 2.
        self.assertEqual(self.tenant.current_api_usage, 2)


class ResetDailyUsageTests(TestCase):
    def setUp(self):
        self.tier = SubscriptionTier.objects.create(
            name="PRO",
            monthly_price=Decimal("49.99"),
            api_call_limit=1000,
        )

    def test_resets_usage_to_zero_across_all_tenants(self):
        TenantAccount.objects.create(
            company_name="Acme Corp",
            billing_email="billing@acme.example",
            tier=self.tier,
            current_api_usage=800,
        )
        TenantAccount.objects.create(
            company_name="Beta LLC",
            billing_email="billing@beta.example",
            tier=self.tier,
            current_api_usage=250,
        )

        updated_count = reset_daily_usage()

        self.assertEqual(updated_count, 2)
        for tenant in TenantAccount.objects.all():
            self.assertEqual(tenant.current_api_usage, 0)

    def test_returns_zero_when_no_tenants_exist(self):
        self.assertEqual(reset_daily_usage(), 0)


class UpdateTenantStatusTests(TestCase):
    def setUp(self):
        self.tier = SubscriptionTier.objects.create(
            name="BASIC",
            monthly_price=Decimal("9.99"),
            api_call_limit=1000,
        )
        self.tenant = TenantAccount.objects.create(
            company_name="Acme Corp",
            billing_email="billing@acme.example",
            tier=self.tier,
        )

    def test_transitions_status_successfully(self):
        updated = update_tenant_status(
            self.tenant.id, TenantAccount.STATUS_PAST_DUE
        )
        self.assertEqual(updated.status, TenantAccount.STATUS_PAST_DUE)

        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, TenantAccount.STATUS_PAST_DUE)

    def test_rejects_invalid_status_value(self):
        with self.assertRaises(ValueError):
            update_tenant_status(self.tenant.id, "NOT_A_REAL_STATUS")

        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, TenantAccount.STATUS_ACTIVE)

    def test_raises_does_not_exist_for_unknown_tenant(self):
        with self.assertRaises(TenantAccount.DoesNotExist):
            update_tenant_status(999999, TenantAccount.STATUS_CANCELED)
