from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class PasswordResetToken:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None

    @classmethod
    def create(cls, user_id: str, token_hash: str, expires_at: datetime) -> "PasswordResetToken":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
            used_at=None,
        )

    def mark_used(self) -> "PasswordResetToken":
        return replace(self, used_at=datetime.now(timezone.utc))
