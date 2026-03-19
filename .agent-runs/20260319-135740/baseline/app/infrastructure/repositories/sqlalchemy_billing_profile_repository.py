from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.entities.billing_profile import BillingProfile
from app.domain.repositories.billing_profile_repository import BillingProfileRepository
from app.infrastructure.database.models import BillingProfileModel


def _to_entity(model: BillingProfileModel) -> BillingProfile:
    return BillingProfile(
        id=str(model.id),
        user_id=str(model.user_id),
        company_name=model.company_name,
        billing_email=model.billing_email,
        plan_name=model.plan_name,
        tax_id=model.tax_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyBillingProfileRepository(BillingProfileRepository):
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def add(self, profile: BillingProfile) -> BillingProfile:
        model = BillingProfileModel(
            id=UUID(profile.id),
            user_id=UUID(profile.user_id),
            company_name=profile.company_name,
            billing_email=profile.billing_email,
            plan_name=profile.plan_name,
            tax_id=profile.tax_id,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
        self.db_session.add(model)
        self.db_session.commit()
        self.db_session.refresh(model)
        return _to_entity(model)

    def get_by_user_id(self, user_id: str) -> BillingProfile | None:
        model = (
            self.db_session.query(BillingProfileModel)
            .filter(BillingProfileModel.user_id == UUID(user_id))
            .one_or_none()
        )
        return _to_entity(model) if model is not None else None

    def update(self, profile: BillingProfile) -> BillingProfile:
        model = self.db_session.get(BillingProfileModel, UUID(profile.id))
        if model is None:
            raise ValueError("Billing profile not found.")

        model.company_name = profile.company_name
        model.billing_email = profile.billing_email
        model.plan_name = profile.plan_name
        model.tax_id = profile.tax_id
        model.updated_at = profile.updated_at
        self.db_session.commit()
        self.db_session.refresh(model)
        return _to_entity(model)
