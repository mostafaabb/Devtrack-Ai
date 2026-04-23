"""
Email Service — Transactional emails for the platform.
Supports SMTP (SendGrid, Mailgun, AWS SES, Gmail) with HTML templates.
Falls back to logging in development mode.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger("devtrack.email")


class EmailService:
    """
    Central email dispatch service.
    
    Supports:
    - Welcome emails
    - Email verification
    - Password reset
    - Order confirmation
    - Booking confirmation
    - Staff invitation
    - Notification alerts
    """

    def _get_smtp_connection(self):
        """Create SMTP connection based on settings."""
        if not settings.SMTP_HOST:
            return None
        try:
            if settings.SMTP_USE_TLS:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
            
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            return server
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            return None

    def _send_email(self, to: str, subject: str, html_body: str, text_body: str = "") -> bool:
        """Send an email via SMTP."""
        if not settings.SMTP_HOST:
            logger.info(f"📧 [DEV MODE] Email to {to}: {subject}")
            logger.debug(f"   Body: {text_body[:200]}")
            return True

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.APP_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            server = self._get_smtp_connection()
            if server:
                server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
                server.quit()
                logger.info(f"✅ Email sent to {to}: {subject}")
                return True
            else:
                logger.warning(f"⚠️ Could not send email to {to} — SMTP unavailable")
                return False
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
            return False

    def _base_template(self, content: str, business_name: str = "DevTrack AI") -> str:
        """Wrap content in a branded HTML email template."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a3e; border-radius: 16px; overflow: hidden; border: 1px solid rgba(99,102,241,0.2); }}
                .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .body {{ padding: 30px; color: #e2e8f0; line-height: 1.6; }}
                .body h2 {{ color: #a5b4fc; margin-top: 0; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white !important; padding: 14px 32px; border-radius: 10px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .footer {{ padding: 20px 30px; color: #64748b; font-size: 12px; text-align: center; border-top: 1px solid rgba(99,102,241,0.1); }}
                .code {{ background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 12px 20px; border-radius: 8px; font-size: 28px; letter-spacing: 6px; text-align: center; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 {business_name}</h1>
                </div>
                <div class="body">
                    {content}
                </div>
                <div class="footer">
                    &copy; {datetime.utcnow().year} {business_name}. All rights reserved.<br>
                    Powered by DevTrack AI Platform
                </div>
            </div>
        </body>
        </html>
        """

    # ─── Email Templates ─────────────────────────────────────

    def send_welcome(self, to: str, full_name: str, business_name: str) -> bool:
        """Send welcome email after registration."""
        content = f"""
        <h2>Welcome aboard, {full_name}! 🎉</h2>
        <p>Your business <strong>{business_name}</strong> has been successfully set up on DevTrack AI.</p>
        <p>Here's what you can do now:</p>
        <ul>
            <li>📦 Set up your products and services</li>
            <li>🤖 Configure your AI assistant</li>
            <li>📱 Connect your WhatsApp Business</li>
            <li>📂 Upload documents for AI knowledge base</li>
            <li>⚡ Create automation workflows</li>
        </ul>
        <p>Need help? Our support team is always here for you.</p>
        """
        return self._send_email(to, f"Welcome to {business_name}!", self._base_template(content, business_name))

    def send_verification_code(self, to: str, code: str, full_name: str) -> bool:
        """Send email verification code."""
        content = f"""
        <h2>Verify your email address</h2>
        <p>Hi {full_name},</p>
        <p>Enter this verification code to confirm your email:</p>
        <div class="code">{code}</div>
        <p style="margin-top: 20px; color: #94a3b8;">This code expires in 30 minutes.</p>
        <p>If you didn't create an account, you can safely ignore this email.</p>
        """
        return self._send_email(to, f"Your verification code: {code}", self._base_template(content))

    def send_password_reset(self, to: str, reset_token: str, full_name: str) -> bool:
        """Send password reset link."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        content = f"""
        <h2>Reset your password</h2>
        <p>Hi {full_name},</p>
        <p>We received a request to reset your password. Click the button below:</p>
        <p style="text-align: center;"><a href="{reset_url}" class="btn">Reset Password</a></p>
        <p style="color: #94a3b8;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        """
        return self._send_email(to, "Reset your password", self._base_template(content))

    def send_order_confirmation(self, to: str, customer_name: str, order_number: str,
                                 items: list, total: float, business_name: str) -> bool:
        """Send order confirmation to customer."""
        items_html = "".join([
            f"<tr><td style='padding:8px;color:#e2e8f0;'>{item['name']}</td>"
            f"<td style='padding:8px;color:#e2e8f0;text-align:center;'>{item['quantity']}</td>"
            f"<td style='padding:8px;color:#e2e8f0;text-align:right;'>${item['price']:.2f}</td></tr>"
            for item in items
        ])
        content = f"""
        <h2>Order Confirmed! ✅</h2>
        <p>Hi {customer_name},</p>
        <p>Your order <strong>#{order_number}</strong> has been confirmed.</p>
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
            <thead>
                <tr style="border-bottom:1px solid rgba(99,102,241,0.3);">
                    <th style="padding:8px;text-align:left;color:#a5b4fc;">Item</th>
                    <th style="padding:8px;text-align:center;color:#a5b4fc;">Qty</th>
                    <th style="padding:8px;text-align:right;color:#a5b4fc;">Price</th>
                </tr>
            </thead>
            <tbody>{items_html}</tbody>
            <tfoot>
                <tr style="border-top:1px solid rgba(99,102,241,0.3);">
                    <td colspan="2" style="padding:8px;text-align:right;color:#a5b4fc;font-weight:bold;">Total:</td>
                    <td style="padding:8px;text-align:right;color:#10b981;font-weight:bold;">${total:.2f}</td>
                </tr>
            </tfoot>
        </table>
        <p>We'll notify you when your order status changes.</p>
        """
        return self._send_email(to, f"Order #{order_number} Confirmed", self._base_template(content, business_name))

    def send_booking_confirmation(self, to: str, customer_name: str, booking_number: str,
                                   service: str, date: str, time: str, business_name: str) -> bool:
        """Send booking confirmation to customer."""
        content = f"""
        <h2>Booking Confirmed! 📅</h2>
        <p>Hi {customer_name},</p>
        <p>Your booking <strong>#{booking_number}</strong> has been confirmed.</p>
        <div style="background:rgba(99,102,241,0.1);padding:20px;border-radius:10px;margin:20px 0;">
            <p style="margin:5px 0;"><strong style="color:#a5b4fc;">Service:</strong> {service}</p>
            <p style="margin:5px 0;"><strong style="color:#a5b4fc;">Date:</strong> {date}</p>
            <p style="margin:5px 0;"><strong style="color:#a5b4fc;">Time:</strong> {time}</p>
        </div>
        <p>Need to reschedule? Contact us anytime.</p>
        """
        return self._send_email(to, f"Booking #{booking_number} Confirmed", self._base_template(content, business_name))

    def send_staff_invitation(self, to: str, inviter_name: str, business_name: str, invite_token: str) -> bool:
        """Send staff invitation email."""
        invite_url = f"{settings.FRONTEND_URL}/invite?token={invite_token}"
        content = f"""
        <h2>You're invited! 🤝</h2>
        <p><strong>{inviter_name}</strong> has invited you to join <strong>{business_name}</strong> on DevTrack AI.</p>
        <p style="text-align: center;"><a href="{invite_url}" class="btn">Accept Invitation</a></p>
        <p style="color: #94a3b8;">This invitation expires in 7 days.</p>
        """
        return self._send_email(to, f"Join {business_name} on DevTrack AI", self._base_template(content, business_name))

    def send_status_update(self, to: str, customer_name: str, entity_type: str,
                            entity_number: str, new_status: str, business_name: str) -> bool:
        """Send order/booking status update to customer."""
        status_emoji = {
            "confirmed": "✅", "preparing": "👨‍🍳", "ready": "📦",
            "delivered": "🚚", "completed": "🎉", "cancelled": "❌"
        }
        emoji = status_emoji.get(new_status, "📋")
        content = f"""
        <h2>{emoji} {entity_type.title()} Update</h2>
        <p>Hi {customer_name},</p>
        <p>Your {entity_type} <strong>#{entity_number}</strong> status has been updated to:</p>
        <div class="code" style="font-size:18px;letter-spacing:2px;">{new_status.upper()}</div>
        <p style="margin-top:20px;">Thank you for choosing {business_name}!</p>
        """
        return self._send_email(to, f"{entity_type.title()} #{entity_number} — {new_status.title()}",
                                self._base_template(content, business_name))


# Global instance
email_service = EmailService()
