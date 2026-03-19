from abc import ABC, abstractmethod


class EmailService(ABC):
    @abstractmethod
    def send_password_reset(self, email: str, reset_link: str) -> None:
        raise NotImplementedError
