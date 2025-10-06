from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.core.config import settings
import traceback


def send_reset_email(to_email: str, reset_code: str):
    """Send password reset email using SendGrid"""
    try:
        subject = "Your Password Reset Code"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <p>We received a request to reset your password.</p>
                <p>Please use the following reset code:</p>
                <h2 style="color: #2c3e50; font-size: 28px; letter-spacing: 3px; text-align: center;">
                    {reset_code}
                </h2>
                <p>This code will expire in <b>15 minutes</b>.</p>
                <br>
                <p>If you did not request a password reset, please ignore this email.</p>
            </body>
        </html>
        """

        message = Mail(
            from_email=settings.sendgrid_from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        print(f"Reset email sent to {to_email}, status: {response.status_code}")

    except Exception as e:
        print("Failed to send reset email:")
        traceback.print_exc()


def send_verify_email_otp(to_email: str, reset_code: str):
    """Send verification email using SendGrid"""
    try:
        subject = "Your Verification Code"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <p>We received a request to register an account.</p>
                <p>Please use the following verification code:</p>
                <h2 style="color: #2c3e50; font-size: 28px; letter-spacing: 3px; text-align: center;">
                    {reset_code}
                </h2>
                <p>This code will expire in <b>15 minutes</b>.</p>
                <br>
                <p>If you did not request to register, please ignore this email.</p>
            </body>
        </html>
        """

        message = Mail(
            from_email=settings.sendgrid_from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        print(
            f"Verification email sent to {to_email}, status: {response.status_code}"
        )

    except Exception as e:
        print("Failed to send verification email:")
        traceback.print_exc()
