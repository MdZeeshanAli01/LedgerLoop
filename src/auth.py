"""Authentication and access control for Hisaabset."""

from __future__ import annotations

import hmac
import hashlib
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    role: str
    email: str


# Single authorized user and role for the application: Finance Lead
FINANCE_LEAD = User(
    username="admin",
    display_name="Zeeshan Ali",
    role="Finance Lead",
    email="sszeeshu@gmail.com",
)

_VALID_USERNAMES = {"admin", "finance", "sszeeshu@gmail.com"}
def _password_matches(password: str) -> bool:
    encoded_hash = os.getenv("HISAABSET_AUTH_PASSWORD_HASH", "").strip()
    if not encoded_hash:
        return False
    try:
        salt_hex, digest_hex = encoded_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 600_000, dklen=len(expected)
    )
    return hmac.compare_digest(actual, expected)


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Validate credentials and return the Finance Lead user if valid, else None."""
    user_key = username.strip().lower()
    if user_key in _VALID_USERNAMES and _password_matches(password.strip()):
        return FINANCE_LEAD
    return None
