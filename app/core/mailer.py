"""
Email service using MailerSend API.
Provides password reset and email verification functionality with retry logic.
"""
import time
import traceback
from typing import Optional

from mailersend import MailerSendClient, EmailBuilder
from mailersend.exceptions import MailerSendError

from app.core.config import settings


# Initialize MailerSend client
def _get_mailersend_client() -> MailerSendClient:
    """Get MailerSend client instance with API key from settings."""
    return MailerSendClient(api_key=settings.mailersend_api_key)


def _send_email_with_retry(
    to_email: str,
    subject: str,
    html_content: str,
    max_retries: int = 2,
    initial_delay: float = 30.0
) -> bool:
    """
    Send email with exponential backoff retry logic.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        max_retries: Maximum number of retry attempts (default: 2)
        initial_delay: Initial delay in seconds before first retry (default: 30s)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Validate configuration
    if not settings.mailersend_api_key:
        print("ERROR: MAILERSEND_API_KEY is not configured in .env file")
        return False
    
    if not settings.mailersend_from_email:
        print("ERROR: MAILERSEND_FROM_EMAIL is not configured in .env file")
        return False
    
    ms = _get_mailersend_client()
    
    email = (
        EmailBuilder()
        .from_email(settings.mailersend_from_email, "BA Copilot")
        .to_many([{"email": to_email}])
        .subject(subject)
        .html(html_content)
        .text(html_content.replace("<br>", "\n").replace("</p>", "\n"))  # Plain text fallback
        .build()
    )
    
    attempt = 0
    delay = initial_delay
    
    while attempt <= max_retries:
        try:
            response = ms.emails.send(email)
            
            if response.success:
                print(f"Email sent to {to_email}, subject: '{subject}'")
                return True
            else:
                error_info = getattr(response, 'data', 'Unknown error')
                print(f"Email send failed (attempt {attempt + 1}): {error_info}")
                
        except MailerSendError as e:
            print(f"MailerSend API error (attempt {attempt + 1}): {e}")
            # Handle different exception attributes safely
            status_code = getattr(e, 'status_code', 'N/A')
            details = getattr(e, 'details', str(e))
            print(f"Status Code: {status_code}, Details: {details}")
            
        except Exception as e:
            print(f"Unexpected error sending email (attempt {attempt + 1}): {e}")
            traceback.print_exc()
        
        # Retry logic: wait before next attempt
        if attempt < max_retries:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
        
        attempt += 1
    
    print(f"Failed to send email to {to_email} after {max_retries + 1} attempts")
    return False


def send_reset_email(to_email: str, reset_code: str) -> bool:
    """
    Send password reset email using MailerSend.
    
    Args:
        to_email: Recipient email address
        reset_code: 6-digit OTP code for password reset
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = "Your Password Reset Code"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h1 style="color: #2c3e50; text-align: center; margin-bottom: 20px;">Password Reset Request</h1>
                <p style="color: #555;">We received a request to reset your password.</p>
                <p style="color: #555;">Please use the following reset code:</p>
                <div style="background-color: #fff; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <h2 style="color: #2c3e50; font-size: 32px; letter-spacing: 5px; margin: 0;">
                        {reset_code}
                    </h2>
                </div>
                <p style="color: #555;">This code will expire in <b>15 minutes</b>.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #888; font-size: 12px;">If you did not request a password reset, please ignore this email.</p>
            </div>
        </body>
    </html>
    """
    
    return _send_email_with_retry(to_email, subject, html_content)


def send_verify_email_otp(to_email: str, reset_code: str) -> bool:
    """
    Send email verification OTP using MailerSend.
    
    Args:
        to_email: Recipient email address
        reset_code: 6-digit OTP code for email verification
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = "Your Verification Code"
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
                <h1 style="color: #2c3e50; text-align: center; margin-bottom: 20px;">Welcome to BA Copilot!</h1>
                <p style="color: #555;">We received a request to register an account.</p>
                <p style="color: #555;">Please use the following verification code to complete your registration:</p>
                <div style="background-color: #fff; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <h2 style="color: #2c3e50; font-size: 32px; letter-spacing: 5px; margin: 0;">
                        {reset_code}
                    </h2>
                </div>
                <p style="color: #555;">This code will expire in <b>15 minutes</b>.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #888; font-size: 12px;">If you did not request to register, please ignore this email.</p>
            </div>
        </body>
    </html>
    """
    
    return _send_email_with_retry(to_email, subject, html_content)
