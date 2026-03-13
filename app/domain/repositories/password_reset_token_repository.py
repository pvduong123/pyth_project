from abc import ABC, abstractmethod

from app.domain.entities.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        raise NotImplementedError

    @abstractmethod
    def get_active_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        raise NotImplementedError

    @abstractmethod
    def mark_used(self, token_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_all_used_for_user(self, user_id: str) -> None:
        raise NotImplementedError
