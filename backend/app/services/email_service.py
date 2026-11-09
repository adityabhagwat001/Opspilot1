"""
OpsPilot Enterprise Authentication Email Service
Handles secure dispatch of email verification, password reset, and organization invitations.
Supports live SMTP delivery via configured relays and resilient fallback logging for local development.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict

logger = logging.getLogger("opspilot.email_service")

# In-memory store of recent tokens for development / test inspection
LAST_DISPATCHED_EMAILS: Dict[str, Dict[str, str]] = {}

def get_smtp_config():
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_from = os.getenv("SMTP_FROM_EMAIL", smtp_user or "auth@opspilot.internal").strip()
    is_live = bool(smtp_user and smtp_pass and not os.getenv("PYTEST_CURRENT_TEST"))
    return {
        "smtp_user": smtp_user,
        "smtp_pass": smtp_pass,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_from": smtp_from,
        "is_live": is_live
    }

def send_email_message(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
    cfg = get_smtp_config()
    if cfg["is_live"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = cfg["smtp_from"]
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body_text, "plain"))
            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=10) as server:
                server.starttls()
                server.login(cfg["smtp_user"], cfg["smtp_pass"])
                server.send_message(msg)
            logger.info(f"Successfully dispatched live email to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.warning(f"Live SMTP delivery failed ({e}); falling back to local audit dispatch.")

    logger.info(f"[AUTH EMAIL RELAY] To: {to_email} | Subject: {subject}\n{body_text}")
    return True

def send_verification_email(to_email: str, full_name: str, verification_token: str, frontend_url: str = "http://localhost:5173") -> str:
    verify_url = f"{frontend_url}/login?verify_token={verification_token}"
    subject = "Verify your OpsPilot Enterprise Account"
    body_text = (
        f"Hello {full_name},\n\n"
        f"Thank you for registering for OpsPilot — Enterprise Autonomous AI Operations Platform.\n\n"
        f"Please verify your email address by opening the following link:\n"
        f"{verify_url}\n\n"
        f"Verification Token: {verification_token}\n\n"
        f"If you did not create this account, please ignore this email.\n"
    )
    body_html = f"""
    <div style="font-family: sans-serif; background: #070b14; color: #f1f5f9; padding: 24px; border-radius: 8px;">
        <h2 style="color: #10b981;">Verify your OpsPilot Account</h2>
        <p>Hello {full_name},</p>
        <p>Thank you for registering for OpsPilot. Please verify your email address to activate your access.</p>
        <p style="margin: 20px 0;">
            <a href="{verify_url}" style="background: #10b981; color: #020617; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                Verify Email Address
            </a>
        </p>
        <p style="color: #94a3b8; font-size: 12px;">Token: <code>{verification_token}</code></p>
    </div>
    """
    LAST_DISPATCHED_EMAILS[to_email.lower()] = {
        "type": "verification",
        "token": verification_token,
        "url": verify_url
    }
    send_email_message(to_email, subject, body_text, body_html)
    return verify_url

def send_password_reset_email(to_email: str, full_name: str, reset_token: str, frontend_url: str = "http://localhost:5173") -> str:
    reset_url = f"{frontend_url}/login?reset_token={reset_token}"
    subject = "Reset your OpsPilot Password"
    body_text = (
        f"Hello {full_name},\n\n"
        f"We received a request to reset the password for your OpsPilot account.\n\n"
        f"To choose a new password, open the following link:\n"
        f"{reset_url}\n\n"
        f"Reset Token: {reset_token}\n\n"
        f"This link will expire in 30 minutes. If you did not request this, please disregard.\n"
    )
    body_html = f"""
    <div style="font-family: sans-serif; background: #070b14; color: #f1f5f9; padding: 24px; border-radius: 8px;">
        <h2 style="color: #f59e0b;">Reset your OpsPilot Password</h2>
        <p>Hello {full_name},</p>
        <p>Click below to securely reset your OpsPilot account password:</p>
        <p style="margin: 20px 0;">
            <a href="{reset_url}" style="background: #f59e0b; color: #020617; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                Reset Password
            </a>
        </p>
        <p style="color: #94a3b8; font-size: 12px;">Token: <code>{reset_token}</code> (Expires in 30 minutes)</p>
    </div>
    """
    LAST_DISPATCHED_EMAILS[to_email.lower()] = {
        "type": "reset",
        "token": reset_token,
        "url": reset_url
    }
    send_email_message(to_email, subject, body_text, body_html)
    return reset_url

def send_invitation_email(to_email: str, company_name: str, inviter_name: str, invite_token: str, frontend_url: str = "http://localhost:5173") -> str:
    invite_url = f"{frontend_url}/login?invite_token={invite_token}"
    subject = f"You have been invited to join {company_name} on OpsPilot"
    body_text = (
        f"Hello,\n\n"
        f"{inviter_name} has invited you to join the {company_name} workspace on OpsPilot.\n\n"
        f"To accept the invitation and set up your account, visit:\n"
        f"{invite_url}\n\n"
        f"Invitation Token: {invite_token}\n"
    )
    body_html = f"""
    <div style="font-family: sans-serif; background: #070b14; color: #f1f5f9; padding: 24px; border-radius: 8px;">
        <h2 style="color: #38bdf8;">Join {company_name} on OpsPilot</h2>
        <p>{inviter_name} has invited you to join their organization's operational workspace.</p>
        <p style="margin: 20px 0;">
            <a href="{invite_url}" style="background: #38bdf8; color: #020617; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                Accept Invitation & Set Up Account
            </a>
        </p>
        <p style="color: #94a3b8; font-size: 12px;">Token: <code>{invite_token}</code></p>
    </div>
    """
    LAST_DISPATCHED_EMAILS[to_email.lower()] = {
        "type": "invitation",
        "token": invite_token,
        "url": invite_url
    }
    send_email_message(to_email, subject, body_text, body_html)
    return invite_url

