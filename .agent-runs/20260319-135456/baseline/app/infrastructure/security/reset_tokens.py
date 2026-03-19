import hashlib
import secrets

from app.domain.services.reset_token_service import ResetTokenService


class SecureResetTokenService(ResetTokenService):
    def generate(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_token(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
