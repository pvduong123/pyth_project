from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, plain_text: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, plain_text: str, password_hash: str) -> bool:
        raise NotImplementedError
