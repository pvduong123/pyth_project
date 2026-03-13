from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.application.errors import InvalidResetTokenError, ValidationError
from app.domain.entities.password_reset_token import PasswordResetToken
from app.domain.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.email_service import EmailService
from app.domain.services.password_hasher import PasswordHasher
from app.domain.services.reset_token_service import ResetTokenService


class PasswordResetService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: PasswordResetTokenRepository,
        password_hasher: PasswordHasher,
        reset_token_service: ResetTokenService,
        email_service: EmailService,
        reset_token_expire_minutes: int,
    ) -> None:
        self.user_repository = user_repository
        self.token_repository = token_repository
        self.password_hasher = password_hasher
        self.reset_token_service = reset_token_service
        self.email_service = email_service
        self.reset_token_expire_minutes = reset_token_expire_minutes

    def request_password_reset(self, email: str, reset_link_base_url: str) -> None:
        normalized_email = email.strip().lower()
        if not normalized_email:
            return

        user = self.user_repository.get_by_email(normalized_email)
        if user is None or not user.is_active:
            return

        self.token_repository.mark_all_used_for_user(user.id)
        raw_token = self.reset_token_service.generate()
        token_hash = self.reset_token_service.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.reset_token_expire_minutes)
        token = PasswordResetToken.create(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        self.token_repository.add(token)

        reset_link = f"{reset_link_base_url.rstrip('/')}/reset-password?token={quote(raw_token)}"
        self.email_service.send_password_reset(user.email, reset_link)

    def validate_reset_token(self, raw_token: str | None) -> bool:
        return self._get_valid_token(raw_token) is not None

    def reset_password(self, raw_token: str | None, new_password: str) -> None:
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters.")

        token = self._get_valid_token(raw_token)
        if token is None:
            raise InvalidResetTokenError("This reset link is invalid or has expired.")

        user = self.user_repository.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise InvalidResetTokenError("This reset link is invalid or has expired.")

        updated_user = user.with_password(self.password_hasher.hash(new_password))
        self.user_repository.update(updated_user)
        self.token_repository.mark_all_used_for_user(user.id)

    def _get_valid_token(self, raw_token: str | None) -> PasswordResetToken | None:
        if not raw_token:
            return None

        token_hash = self.reset_token_service.hash_token(raw_token)
        token = self.token_repository.get_active_by_token_hash(token_hash)
        if token is None:
            return None

        if token.expires_at <= datetime.now(timezone.utc):
            self.token_repository.mark_used(token.id)
            return None

        return token
