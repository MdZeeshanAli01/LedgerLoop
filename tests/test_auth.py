import hashlib

import pytest

from src.auth import authenticate_user, FINANCE_LEAD


@pytest.fixture(autouse=True)
def configured_password(monkeypatch):
    salt = b"ledgerloop-test-salt"
    digest = hashlib.pbkdf2_hmac(
        "sha256", b"test-password", salt, 600_000, dklen=32
    )
    monkeypatch.setenv(
        "HISAABSET_AUTH_PASSWORD_HASH",
        f"{salt.hex()}${digest.hex()}",
    )


def test_valid_user_authentication():
    user = authenticate_user("admin", "test-password")
    assert user is not None
    assert user == FINANCE_LEAD
    assert user.role == "Finance Lead"
    assert user.display_name == "Zeeshan Ali"


def test_accepted_login_aliases():
    assert authenticate_user("ADMIN", "test-password") == FINANCE_LEAD
    assert authenticate_user("finance", "test-password") == FINANCE_LEAD
    assert authenticate_user("sszeeshu@gmail.com", "test-password") == FINANCE_LEAD


def test_invalid_password_fails():
    assert authenticate_user("admin", "wrongpassword") is None


def test_nonexistent_user_fails():
    assert authenticate_user("unknown_user", "test-password") is None


def test_missing_password_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("HISAABSET_AUTH_PASSWORD_HASH")
    assert authenticate_user("admin", "test-password") is None


def test_default_demo_credentials_work(monkeypatch):
    monkeypatch.delenv("HISAABSET_AUTH_PASSWORD_HASH", raising=False)
    user = authenticate_user("admin", "hisaabset123")
    assert user is not None
    assert user == FINANCE_LEAD
    assert user.role == "Finance Lead"

