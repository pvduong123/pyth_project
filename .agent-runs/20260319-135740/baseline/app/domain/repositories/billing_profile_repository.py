from abc import ABC, abstractmethod

from app.domain.entities.billing_profile import BillingProfile


class BillingProfileRepository(ABC):
    @abstractmethod
    def add(self, profile: BillingProfile) -> BillingProfile:
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> BillingProfile | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, profile: BillingProfile) -> BillingProfile:
        raise NotImplementedError
