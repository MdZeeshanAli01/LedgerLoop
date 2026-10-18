from src.communications import send_via_ses, valid_email


def test_email_validation():
    assert valid_email("unnamedinsect424@gmail.com")
    assert not valid_email("not-an-email")


def test_ses_test_mode_never_delivers(monkeypatch):
    monkeypatch.setenv("HISAABSET_EMAIL_TEST_MODE", "true")
    result = send_via_ses(
        recipient="unnamedinsect424@gmail.com",
        subject="Payment reminder",
        body="₹1000 is due.",
    )

    assert result.status == "test_blocked"
    assert "no email was delivered" in result.message


def test_ses_requires_region_when_live(monkeypatch):
    monkeypatch.setenv("HISAABSET_EMAIL_TEST_MODE", "false")
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    result = send_via_ses(
        recipient="unnamedinsect424@gmail.com",
        subject="Payment reminder",
        body="₹1000 is due.",
    )

    assert result.status == "failed"
    assert "AWS_REGION" in result.message
