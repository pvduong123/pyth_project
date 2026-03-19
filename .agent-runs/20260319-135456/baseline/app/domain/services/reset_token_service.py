from abc import ABC, abstractmethod


class ResetTokenService(ABC):
    @abstractmethod
    def generate(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def hash_token(self, raw_token: str) -> str:
        raise NotImplementedError
