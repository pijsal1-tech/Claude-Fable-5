"""Database fixture module — imports auth to create a cross-file edge."""
from src.auth import hash_password

USERS = {}


def create_user(name: str, password: str) -> None:
    USERS[name] = hash_password(password, salt="pepper")


def get_user(name: str):
    return USERS.get(name)
