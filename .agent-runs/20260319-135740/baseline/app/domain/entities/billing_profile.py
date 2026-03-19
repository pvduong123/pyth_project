from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BillingProfile:
    id: str
    user_id: str
    company_name: str
    billing_email: str
    plan_name: str
    tax_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        user_id: str,
        company_name: str,
        billing_email: str,
        plan_name: str,
        tax_id: str,
    ) -> "BillingProfile":
        timestamp = datetime.now(timezone.utc)
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            company_name=company_name,
            billing_email=billing_email,
            plan_name=plan_name,
            tax_id=tax_id,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def with_updates(
        self,
        company_name: str,
        billing_email: str,
        plan_name: str,
        tax_id: str,
    ) -> "BillingProfile":
        return replace(
            self,
            company_name=company_name,
            billing_email=billing_email,
            plan_name=plan_name,
            tax_id=tax_id,
            updated_at=datetime.now(timezone.utc),
        )
