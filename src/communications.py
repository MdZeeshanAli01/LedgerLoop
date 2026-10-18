"""Human-approved customer communication through Amazon SES."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr


@dataclass(frozen=True)
class SendResult:
    status: str
    message: str
    provider_message_id: str | None = None
    sent_at: datetime | None = None


def valid_email(value: str) -> bool:
    _, address = parseaddr(value.strip())
    return bool(address and "@" in address and "." in address.rsplit("@", 1)[-1])


def send_via_ses(
    *,
    recipient: str,
    subject: str,
    body: str,
    sender: str | None = None,
) -> SendResult:
    """Send one approved email, or explicitly report why delivery is blocked."""
    sender_address = (sender or os.getenv(
        "HISAABSET_EMAIL_SENDER", "sszeeshu@gmail.com"
    )).strip()
    if not valid_email(sender_address):
        return SendResult("failed", "The configured sender email is invalid.")
    if not valid_email(recipient):
        return SendResult("failed", "The customer email is invalid.")
    if not subject.strip() or not body.strip():
        return SendResult("failed", "Email subject and body are required.")

    test_mode = os.getenv("HISAABSET_EMAIL_TEST_MODE", "true").lower() in {
        "1", "true", "yes", "on"
    }
    if test_mode:
        return SendResult(
            "test_blocked",
            "Test mode is enabled; no email was delivered. "
            "Set HISAABSET_EMAIL_TEST_MODE=false only after SES is configured.",
        )

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    if not region:
        return SendResult("failed", "AWS_REGION is required for Amazon SES.")

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return SendResult(
            "failed",
            "The boto3 package is not installed. Install requirements.txt first.",
        )

    try:
        client = boto3.client("ses", region_name=region)
        response = client.send_email(
            Source=sender_address,
            Destination={"ToAddresses": [recipient.strip()]},
            Message={
                "Subject": {"Data": subject.strip(), "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body.strip(), "Charset": "UTF-8"}},
            },
        )
    except (BotoCoreError, ClientError) as error:
        err_str = str(error)
        if "MessageRejected" in err_str and "Email address is not verified" in err_str:
            try:
                client.verify_email_identity(EmailAddress=recipient.strip())
                return SendResult(
                    "failed",
                    f"AWS SES Sandbox Restriction: Recipient '{recipient.strip()}' is not yet verified. "
                    f"A verification link has just been dispatched to '{recipient.strip()}'. "
                    f"Please click the verification link in that inbox. "
                    f"For instant testing without waiting, you can send to verified address: '{sender_address}'.",
                )
            except Exception:
                pass
        return SendResult("failed", f"Amazon SES could not send the email: {error}")

    return SendResult(
        "sent",
        "Email accepted by Amazon SES.",
        provider_message_id=response.get("MessageId"),
        sent_at=datetime.now(timezone.utc),
    )


def verify_recipient_in_ses(email: str, region: str | None = None) -> tuple[bool, str]:
    """Request an SES verification email for an unverified recipient in Sandbox mode."""
    if not valid_email(email):
        return False, "Invalid email address format."
    reg = region or os.getenv("AWS_REGION", "ap-south-1")
    try:
        import boto3
        client = boto3.client("ses", region_name=reg)
        client.verify_email_identity(EmailAddress=email.strip())
        return True, f"Verification link dispatched to '{email.strip()}'. Check your inbox."
    except Exception as exc:
        return False, f"Could not request verification: {exc}"

