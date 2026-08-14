from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.subscriptions.models import SubscriptionTier, TenantAccount


class SubscriptionTierModelTests(TestCase):
    def test_free_tier_zero_price_saves_successfully(self):
        tier = SubscriptionTier.objects.create(
            name="FREE",
            monthly_price=Decimal("0.00"),
            api_call_limit=100,
        )
        self.assertEqual(tier.monthly_price, Decimal("0.00"))
        self.assertTrue(SubscriptionTier.objects.filter(pk=tier.pk).exists())

    def test_negative_price_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SubscriptionTier.objects.create(
                    name="INVALID",
                    monthly_price=Decimal("-10.00"),
                    api_call_limit=100,
                )

    def test_zero_api_call_limit_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SubscriptionTier.objects.create(
                    name="INVALID_LIMIT",
                    monthly_price=Decimal("10.00"),
                    api_call_limit=0,
                )

    def test_name_uniqueness_enforced(self):
        SubscriptionTier.objects.create(
            name="PRO", monthly_price=Decimal("49.99"), api_call_limit=5000
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SubscriptionTier.objects.create(
                    name="PRO",
                    monthly_price=Decimal("59.99"),
                    api_call_limit=6000,
                )

    def test_decimal_price_math_has_no_float_rounding_error(self):
        tier = SubscriptionTier.objects.create(
            name="PRECISE",
            monthly_price=Decimal("19.99"),
            api_call_limit=1000,
        )
        # Three months of billing summed as Decimal must be exact; the
        # classic float pitfall (0.1 + 0.2 != 0.3) does not apply here.
        total = tier.monthly_price + tier.monthly_price + tier.monthly_price
        self.assertEqual(total, Decimal("59.97"))
        self.assertNotEqual(total, Decimal("59.96999999999999"))


class TenantAccountModelTests(TestCase):
    def setUp(self):
        self.tier = SubscriptionTier.objects.create(
            name="BASIC",
            monthly_price=Decimal("9.99"),
            api_call_limit=1000,
        )

    def test_tenant_creation_with_default_status_and_usage(self):
        tenant = TenantAccount.objects.create(
            company_name="Acme Corp",
            billing_email="billing@acme.example",
            tier=self.tier,
        )
        self.assertEqual(tenant.status, TenantAccount.STATUS_ACTIVE)
        self.assertEqual(tenant.current_api_usage, 0)
        self.assertEqual(tenant.tier, self.tier)

    def test_relationship_related_name_access(self):
        tenant = TenantAccount.objects.create(
            company_name="Beta LLC",
            billing_email="billing@beta.example",
            tier=self.tier,
        )
        self.assertIn(tenant, self.tier.tenants.all())

    def test_deleting_tier_with_active_tenants_raises_protected_error(self):
        TenantAccount.objects.create(
            company_name="Gamma Inc",
            billing_email="billing@gamma.example",
            tier=self.tier,
        )
        with self.assertRaises(ProtectedError):
            self.tier.delete()

    def test_deleting_tier_without_tenants_succeeds(self):
        empty_tier = SubscriptionTier.objects.create(
            name="UNUSED",
            monthly_price=Decimal("5.00"),
            api_call_limit=10,
        )
        empty_tier.delete()
        self.assertFalse(
            SubscriptionTier.objects.filter(name="UNUSED").exists()
        )

    def test_has_exceeded_quota_false_when_under_limit(self):
        tenant = TenantAccount.objects.create(
            company_name="Delta Co",
            billing_email="billing@delta.example",
            tier=self.tier,
            current_api_usage=500,
        )
        self.assertFalse(tenant.has_exceeded_quota())
        

    def test_has_exceeded_quota_true_when_at_limit(self):
        tenant = TenantAccount.objects.create(
            company_name="Epsilon Co",
            billing_email="billing@epsilon.example",
            tier=self.tier,
            current_api_usage=1000,
        )
        self.assertTrue(tenant.has_exceeded_quota())

    def test_has_exceeded_quota_true_when_over_limit(self):
        tenant = TenantAccount.objects.create(
            company_name="Zeta Co",
            billing_email="billing@zeta.example",
            tier=self.tier,
            current_api_usage=1500,
        )
        self.assertTrue(tenant.has_exceeded_quota())

    def test_is_operational_true_for_active_status(self):
        tenant = TenantAccount.objects.create(
            company_name="Eta Co",
            billing_email="billing@eta.example",
            tier=self.tier,
            status=TenantAccount.STATUS_ACTIVE,
        )
        self.assertTrue(tenant.is_operational())

    def test_is_operational_false_for_past_due_status(self):
        tenant = TenantAccount.objects.create(
            company_name="Theta Co",
            billing_email="billing@theta.example",
            tier=self.tier,
            status=TenantAccount.STATUS_PAST_DUE,
        )
        self.assertFalse(tenant.is_operational())

    def test_is_operational_false_for_canceled_status(self):
        tenant = TenantAccount.objects.create(
            company_name="Iota Co",
            billing_email="billing@iota.example",
            tier=self.tier,
            status=TenantAccount.STATUS_CANCELED,
        )
        self.assertFalse(tenant.is_operational())
