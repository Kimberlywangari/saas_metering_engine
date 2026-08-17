from django.db import models

# Create your models here.from django.db import models
from django.db.models import Q


class SubscriptionTier(models.Model):
    
    name = models.CharField(max_length=50, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    api_call_limit = models.PositiveIntegerField(
        help_text="Maximum number of API calls a tenant on this tier may "
        "make per day."
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(monthly_price__gte=0),
                name="subscriptiontier_monthly_price_gte_0",
            ),
            models.CheckConstraint(
                check=Q(api_call_limit__gt=0),
                name="subscriptiontier_api_call_limit_gt_0",
            ),
        ]
        ordering = ["monthly_price"]

    def __str__(self) -> str:
        return f"{self.name} (${self.monthly_price}/mo)"


class TenantAccount(models.Model):
    """
    A customer/company account subscribed to a SubscriptionTier.

    This is the "many" side of the one-to-many relationship: many tenants
    can point at the same tier via a ForeignKey. PROTECT prevents a tier
    from being deleted while tenants still reference it.
    """

    STATUS_ACTIVE = "ACTIVE"
    STATUS_PAST_DUE = "PAST_DUE"
    STATUS_CANCELED = "CANCELED"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past Due"),
        (STATUS_CANCELED, "Canceled"),
    ]

    company_name = models.CharField(max_length=100)
    billing_email = models.EmailField()
    tier = models.ForeignKey(
        SubscriptionTier,
        on_delete=models.PROTECT,
        related_name="tenants",
    )
    current_api_usage = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_name"]

    def __str__(self) -> str:
        return f"{self.company_name} [{self.tier.name}]"

    def has_exceeded_quota(self) -> bool:
        """True once usage has reached or passed the tier's daily limit."""
        return self.current_api_usage >= self.tier.api_call_limit

    def is_operational(self) -> bool:
        """True only when the account is in good standing (ACTIVE)."""
        return self.status == self.STATUS_ACTIVE