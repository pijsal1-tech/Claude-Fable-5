"""Auth module fixture: definitions + callers for SymbolIndex tests."""
import hashlib


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(password: str, salt: str, expected: str) -> bool:
    return hash_password(password, salt) == expected


class AuthService:
    def __init__(self, salt: str = "pepper"):
        self.salt = salt

    def login(self, user: str, password: str, stored_hash: str) -> bool:
        return verify_password(password, self.salt, stored_hash)
