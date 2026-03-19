from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuthTokenClaims:
    user_id: str
    issued_at: datetime


class AuthTokenService(ABC):
    @abstractmethod
    def issue_access_token(self, user_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_claims(self, token: str) -> AuthTokenClaims | None:
        raise NotImplementedError
