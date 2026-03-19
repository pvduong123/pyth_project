from app.application.errors import ValidationError
from app.domain.entities.billing_profile import BillingProfile
from app.domain.repositories.billing_profile_repository import BillingProfileRepository


class BillingService:
    def __init__(self, billing_repository: BillingProfileRepository) -> None:
        self.billing_repository = billing_repository

    def get_or_create_profile(self, user_id: str, email: str) -> BillingProfile:
        existing_profile = self.billing_repository.get_by_user_id(user_id)
        if existing_profile is not None:
            return existing_profile

        profile = BillingProfile.create(
            user_id=user_id,
            company_name="",
            billing_email=email,
            plan_name="Starter",
            tax_id="",
        )
        return self.billing_repository.add(profile)

    def update_profile(
        self,
        user_id: str,
        company_name: str,
        billing_email: str,
        plan_name: str,
        tax_id: str,
    ) -> BillingProfile:
        if not billing_email.strip():
            raise ValidationError("Billing email is required.")

        profile = self.get_or_create_profile(user_id=user_id, email=billing_email)
        updated = profile.with_updates(
            company_name=company_name.strip(),
            billing_email=billing_email.strip().lower(),
            plan_name=plan_name.strip() or "Starter",
            tax_id=tax_id.strip(),
        )
        return self.billing_repository.update(updated)
