from pwdlib import PasswordHash

from app.domain.services.password_hasher import PasswordHasher


class PwdlibPasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self.password_hash = PasswordHash.recommended()

    def hash(self, plain_text: str) -> str:
        return self.password_hash.hash(plain_text)

    def verify(self, plain_text: str, password_hash: str) -> bool:
        return self.password_hash.verify(plain_text, password_hash)
