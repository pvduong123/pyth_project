from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.domain.services.auth_token_service import AuthTokenClaims, AuthTokenService


class JwtTokenService(AuthTokenService):
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def issue_access_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.expire_minutes)).timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def get_claims(self, token: str) -> AuthTokenClaims | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except InvalidTokenError:
            return None

        user_id = payload.get("sub")
        issued_at = payload.get("iat")
        if not isinstance(user_id, str) or not user_id or not isinstance(issued_at, int):
            return None

        return AuthTokenClaims(
            user_id=user_id,
            issued_at=datetime.fromtimestamp(issued_at, tz=timezone.utc),
        )
