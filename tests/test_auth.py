from src.auth import authenticate_user, FINANCE_LEAD


def test_valid_user_authentication():
    user = authenticate_user("admin", "hisaabset123")
    assert user is not None
    assert user == FINANCE_LEAD
    assert user.role == "Finance Lead"
    assert user.display_name == "Zeeshan Ali"


def test_accepted_login_aliases():
    assert authenticate_user("ADMIN", "hisaabset123") == FINANCE_LEAD
    assert authenticate_user("finance", "hisaabset123") == FINANCE_LEAD
    assert authenticate_user("sszeeshu@gmail.com", "hisaabset123") == FINANCE_LEAD


def test_invalid_password_fails():
    assert authenticate_user("admin", "wrongpassword") is None


def test_nonexistent_user_fails():
    assert authenticate_user("unknown_user", "hisaabset123") is None
