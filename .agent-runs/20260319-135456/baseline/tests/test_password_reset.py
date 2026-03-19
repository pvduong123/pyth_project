from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.application.auth_service import AuthService
from app.application.errors import InvalidCredentialsError, InvalidResetTokenError
from app.application.password_reset_service import PasswordResetService
from app.domain.entities.password_reset_token import PasswordResetToken
from app.domain.entities.user import User
from app.domain.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.auth_token_service import AuthTokenClaims, AuthTokenService
from app.domain.services.email_service import EmailService
from app.domain.services.password_hasher import PasswordHasher
from app.domain.services.reset_token_service import ResetTokenService


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = {user.id: user for user in (users or [])}

    def add(self, user: User) -> User:
        self.users[user.id] = user
        return user

    def get_by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def get_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def update(self, user: User) -> User:
        self.users[user.id] = user
        return user


class InMemoryPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self) -> None:
        self.tokens: dict[str, PasswordResetToken] = {}

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        self.tokens[token.id] = token
        return token

    def get_active_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        for token in self.tokens.values():
            if token.token_hash == token_hash and token.used_at is None:
                return token
        return None

    def mark_used(self, token_id: str) -> None:
        token = self.tokens.get(token_id)
        if token is not None:
            self.tokens[token_id] = token.mark_used()

    def mark_all_used_for_user(self, user_id: str) -> None:
        for token_id, token in list(self.tokens.items()):
            if token.user_id == user_id and token.used_at is None:
                self.tokens[token_id] = token.mark_used()


class StubPasswordHasher(PasswordHasher):
    def hash(self, plain_text: str) -> str:
        return f"hashed:{plain_text}"

    def verify(self, plain_text: str, password_hash: str) -> bool:
        return password_hash == self.hash(plain_text)


class StubResetTokenService(ResetTokenService):
    def __init__(self) -> None:
        self.counter = 0

    def generate(self) -> str:
        self.counter += 1
        return f"reset-token-{self.counter}"

    def hash_token(self, raw_token: str) -> str:
        return f"reset-hash:{raw_token}"


class CapturingEmailService(EmailService):
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send_password_reset(self, email: str, reset_link: str) -> None:
        self.messages.append((email, reset_link))


class StubAuthTokenService(AuthTokenService):
    def __init__(self) -> None:
        self.claims: dict[str, AuthTokenClaims] = {}

    def issue_access_token(self, user_id: str) -> str:
        token = f"jwt:{user_id}:{len(self.claims) + 1}"
        self.claims[token] = AuthTokenClaims(
            user_id=user_id,
            issued_at=datetime.now(timezone.utc),
        )
        return token

    def add_token(self, token: str, claims: AuthTokenClaims) -> None:
        self.claims[token] = claims

    def get_claims(self, token: str) -> AuthTokenClaims | None:
        return self.claims.get(token)


class PasswordResetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user = User.create(
            email="person@example.com",
            full_name="Example User",
            password_hash="hashed:oldpassword123",
        )
        self.users = InMemoryUserRepository([self.user])
        self.tokens = InMemoryPasswordResetTokenRepository()
        self.password_hasher = StubPasswordHasher()
        self.reset_token_service = StubResetTokenService()
        self.email_service = CapturingEmailService()
        self.service = PasswordResetService(
            user_repository=self.users,
            token_repository=self.tokens,
            password_hasher=self.password_hasher,
            reset_token_service=self.reset_token_service,
            email_service=self.email_service,
            reset_token_expire_minutes=30,
        )

    def test_request_password_reset_creates_token_and_sends_link(self) -> None:
        self.service.request_password_reset(
            email=" person@example.com ",
            reset_link_base_url="http://localhost:8000/",
        )

        self.assertEqual(len(self.tokens.tokens), 1)
        stored_token = next(iter(self.tokens.tokens.values()))
        self.assertEqual(stored_token.user_id, self.user.id)
        self.assertEqual(stored_token.token_hash, "reset-hash:reset-token-1")
        self.assertIsNone(stored_token.used_at)
        self.assertEqual(
            self.email_service.messages,
            [("person@example.com", "http://localhost:8000/reset-password?token=reset-token-1")],
        )

    def test_reset_password_updates_password_marks_tokens_used_and_blocks_reuse(self) -> None:
        self.service.request_password_reset(
            email="person@example.com",
            reset_link_base_url="http://localhost:8000",
        )

        self.service.reset_password("reset-token-1", "newpassword456")

        updated_user = self.users.get_by_id(self.user.id)
        self.assertIsNotNone(updated_user)
        assert updated_user is not None
        self.assertEqual(updated_user.password_hash, "hashed:newpassword456")
        self.assertIsNotNone(updated_user.password_changed_at)

        stored_token = next(iter(self.tokens.tokens.values()))
        self.assertIsNotNone(stored_token.used_at)
        self.assertFalse(self.service.validate_reset_token("reset-token-1"))

        with self.assertRaises(InvalidResetTokenError):
            self.service.reset_password("reset-token-1", "anotherpassword789")

    def test_password_change_invalidates_older_access_tokens(self) -> None:
        auth_tokens = StubAuthTokenService()
        auth_service = AuthService(
            user_repository=self.users,
            password_hasher=self.password_hasher,
            auth_token_service=auth_tokens,
        )

        old_iat = datetime.now(timezone.utc) - timedelta(minutes=10)
        auth_tokens.add_token("old-token", AuthTokenClaims(user_id=self.user.id, issued_at=old_iat))

        self.service.request_password_reset(
            email="person@example.com",
            reset_link_base_url="http://localhost:8000",
        )
        self.service.reset_password("reset-token-1", "newpassword456")

        self.assertIsNone(auth_service.get_user_by_access_token("old-token"))

        new_user = self.users.get_by_id(self.user.id)
        assert new_user is not None
        fresh_iat = new_user.password_changed_at + timedelta(seconds=1)
        auth_tokens.add_token("fresh-token", AuthTokenClaims(user_id=self.user.id, issued_at=fresh_iat))

        self.assertEqual(auth_service.get_user_by_access_token("fresh-token"), new_user)
        self.assertEqual(
            auth_service.authenticate("person@example.com", "newpassword456"),
            new_user,
        )
        with self.assertRaises(InvalidCredentialsError):
            auth_service.authenticate("person@example.com", "oldpassword123")

    def test_request_password_reset_silently_ignores_unknown_email(self) -> None:
        self.service.request_password_reset(
            email="missing@example.com",
            reset_link_base_url="http://localhost:8000",
        )

        self.assertEqual(self.email_service.messages, [])
        self.assertEqual(self.tokens.tokens, {})


if __name__ == "__main__":
    unittest.main()
