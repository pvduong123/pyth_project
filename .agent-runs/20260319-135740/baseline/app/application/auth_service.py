from __future__ import annotations

from app.application.errors import DuplicateEmailError, InvalidCredentialsError, ValidationError
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.auth_token_service import AuthTokenService
from app.domain.services.password_hasher import PasswordHasher


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        auth_token_service: AuthTokenService,
    ) -> None:
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.auth_token_service = auth_token_service

    def register_user(self, email: str, password: str, full_name: str) -> User:
        normalized_email = email.strip().lower()
        full_name = full_name.strip()

        if not normalized_email or not password or not full_name:
            raise ValidationError("Email, password, and full name are required.")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters.")

        existing_user = self.user_repository.get_by_email(normalized_email)
        if existing_user is not None:
            raise DuplicateEmailError("An account with that email already exists.")

        password_hash = self.password_hasher.hash(password)
        user = User.create(email=normalized_email, full_name=full_name, password_hash=password_hash)
        return self.user_repository.add(user)

    def authenticate(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        user = self.user_repository.get_by_email(normalized_email)
        if user is None or not self.password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        if not user.is_active:
            raise InvalidCredentialsError("This account is inactive.")
        return user

    def create_access_token(self, user_id: str) -> str:
        return self.auth_token_service.issue_access_token(user_id)

    def get_user_by_access_token(self, raw_token: str | None) -> User | None:
        if not raw_token:
            return None

        claims = self.auth_token_service.get_claims(raw_token)
        if claims is None:
            return None

        user = self.user_repository.get_by_id(claims.user_id)
        if user is None:
            return None

        if user.password_changed_at is not None and claims.issued_at < user.password_changed_at:
            return None

        return user
