from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    full_name: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    password_changed_at: datetime | None

    @classmethod
    def create(cls, email: str, full_name: str, password_hash: str) -> "User":
        timestamp = datetime.now(timezone.utc)
        return cls(
            id=str(uuid4()),
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            is_active=True,
            created_at=timestamp,
            updated_at=timestamp,
            password_changed_at=None,
        )

    def with_updates(self, full_name: str) -> "User":
        return replace(self, full_name=full_name, updated_at=datetime.now(timezone.utc))

    def with_password(self, password_hash: str) -> "User":
        timestamp = datetime.now(timezone.utc)
        return replace(
            self,
            password_hash=password_hash,
            updated_at=timestamp,
            password_changed_at=timestamp,
        )
