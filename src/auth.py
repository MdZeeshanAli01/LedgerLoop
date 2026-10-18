"""Authentication and access control for Hisaabset."""

from __future__ import annotations

import hmac
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
_PASSWORD = "hisaabset123"


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Validate credentials and return the Finance Lead user if valid, else None."""
    user_key = username.strip().lower()
    if user_key in _VALID_USERNAMES and hmac.compare_digest(password.strip(), _PASSWORD):
        return FINANCE_LEAD
    return None
