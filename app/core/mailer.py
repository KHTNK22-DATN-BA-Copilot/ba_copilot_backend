"""
Email service using SendGrid API.
Provides password reset and email verification functionality with retry logic.
"""

import time
import traceback

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


def _get_sendgrid_client() -> SendGridAPIClient:
    """Get SendGrid client instance."""
    return SendGridAPIClient(settings.sendgrid_api_key)


def _build_otp_email(
    title: str,
    description: str,
    code: str,
    footer_message: str,
) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>

    <body style="
        margin:0;
        padding:0;
        background:#f4f7fb;
        font-family:Arial,Helvetica,sans-serif;
    ">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center" style="padding:40px 20px;">

                <table
                    width="600"
                    cellpadding="0"
                    cellspacing="0"
                    style="
                        background:#ffffff;
                        border-radius:16px;
                        overflow:hidden;
                        box-shadow:0 4px 20px rgba(0,0,0,0.08);
                    "
                >

                    <!-- Header -->
                    <tr>
                        <td
                            align="center"
                            style="
                                background:#986650;
                                padding:40px 20px;
                            "
                        >
                            <h1
                                style="
                                    color:white;
                                    margin:0;
                                    font-size:28px;
                                "
                            >
                                BA Copilot
                            </h1>

                            <p
                                style="
                                    color:#f3f4f6;
                                    margin-top:10px;
                                    font-size:14px;
                                "
                            >
                                AI-Powered Business Analysis Platform
                            </p>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding:40px;">

                            <h2
                                style="
                                    color:#1f2937;
                                    margin-top:0;
                                    text-align:center;
                                "
                            >
                                {title}
                            </h2>

                            <p
                                style="
                                    color:#4b5563;
                                    line-height:1.8;
                                    font-size:16px;
                                "
                            >
                                {description}
                            </p>

                            <div
                                style="
                                    background:#f8fafc;
                                    border:2px dashed #986650;
                                    border-radius:12px;
                                    padding:24px;
                                    text-align:center;
                                    margin:30px 0;
                                "
                            >
                                <div
                                    style="
                                        font-size:40px;
                                        font-weight:bold;
                                        letter-spacing:8px;
                                        color:#986650;
                                    "
                                >
                                    {code}
                                </div>
                            </div>

                            <p
                                style="
                                    color:#4b5563;
                                    font-size:15px;
                                "
                            >
                                This code will expire in
                                <strong>15 minutes</strong>.
                            </p>

                            <p
                                style="
                                    color:#4b5563;
                                    font-size:15px;
                                "
                            >
                                {footer_message}
                            </p>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td
                            style="
                                background:#f8fafc;
                                border-top:1px solid #e5e7eb;
                                padding:24px;
                                text-align:center;
                            "
                        >
                            <p
                                style="
                                    margin:0;
                                    font-size:13px;
                                    color:#6b7280;
                                "
                            >
                                © BA Copilot. All rights reserved.
                            </p>

                            <p
                                style="
                                    margin-top:8px;
                                    font-size:12px;
                                    color:#9ca3af;
                                "
                            >
                                This is an automated email. Please do not reply.
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """


def _send_email_with_retry(
    to_email: str,
    subject: str,
    html_content: str,
    max_retries: int = 2,
    initial_delay: float = 30.0,
) -> bool:
    """
    Send email with exponential backoff retry logic.
    """

    if not settings.sendgrid_api_key:
        print("ERROR: SENDGRID_API_KEY is not configured")
        return False

    if not settings.sendgrid_from_email:
        print("ERROR: SENDGRID_FROM_EMAIL is not configured")
        return False

    attempt = 0
    delay = initial_delay

    while attempt <= max_retries:
        try:
            message = Mail(
                from_email=settings.sendgrid_from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=(
                    "Your verification code is included in the email body."
                ),
                html_content=html_content,
            )

            sg = _get_sendgrid_client()
            response = sg.send(message)

            if 200 <= response.status_code < 300:
                print(
                    f"Email sent successfully to {to_email}, "
                    f"subject='{subject}', "
                    f"status={response.status_code}"
                )
                return True

            print(
                f"Email send failed (attempt {attempt + 1}), "
                f"status={response.status_code}, "
                f"body={response.body}"
            )

        except Exception as e:
            print(f"Unexpected error sending email (attempt {attempt + 1}): {str(e)}")
            traceback.print_exc()

        if attempt < max_retries:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2

        attempt += 1

    print(f"Failed to send email to {to_email} after {max_retries + 1} attempts")
    return False


def send_reset_email(to_email: str, reset_code: str) -> bool:
    subject = "Reset Your BA Copilot Password"

    html_content = _build_otp_email(
        title="Password Reset Request",
        description=(
            "We received a request to reset your BA Copilot password. "
            "Use the verification code below to continue."
        ),
        code=reset_code,
        footer_message=(
            "If you did not request a password reset, you can safely ignore this email."
        ),
    )

    return _send_email_with_retry(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
    )


def send_verify_email_otp(to_email: str, verify_code: str) -> bool:
    subject = "Verify Your BA Copilot Account"

    html_content = _build_otp_email(
        title="Verify Your Email",
        description=(
            "Welcome to BA Copilot. "
            "Use the verification code below to activate your account."
        ),
        code=verify_code,
        footer_message=(
            "If you did not create an account, you can safely ignore this email."
        ),
    )

    return _send_email_with_retry(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
    )
