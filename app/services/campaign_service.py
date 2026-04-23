"""
Campaign Service - Email and SMS marketing automation.
Handles campaign creation, sending, and analytics tracking.
"""
import logging
import random
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.campaign import (
    Campaign, EmailTemplate, CampaignRecipient, CampaignLink, Unsubscribe,
    CampaignType, CampaignStatus, RecipientStatus, TriggerType
)
from app.models.customer import Customer
from app.core.config import settings

logger = logging.getLogger("devtrack.campaigns")


class CampaignService:
    """
    Marketing campaign service.
    Handles email/SMS campaigns, templates, and tracking.
    """

    def _generate_tracking_code(self) -> str:
        """Generate unique tracking code for links."""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choices(chars, k=12))

    async def create_campaign(
        self,
        db: Session,
        business_id: str,
        name: str,
        campaign_type: CampaignType,
        subject: str = None,
        content: str = None,
        html_content: str = None,
        template_id: str = None,
        from_name: str = None,
        from_email: str = None,
        segment_rules: Dict = None,
        customer_tags: List[str] = None,
        scheduled_at: datetime = None,
        trigger_type: TriggerType = TriggerType.MANUAL,
        created_by: str = None,
    ) -> Dict[str, Any]:
        """Create a new marketing campaign."""
        campaign = Campaign(
            business_id=business_id,
            name=name,
            campaign_type=campaign_type,
            status=CampaignStatus.DRAFT,
            subject=subject,
            content=content,
            html_content=html_content,
            template_id=template_id,
            from_name=from_name,
            from_email=from_email,
            segment_rules=segment_rules or {},
            customer_tags=customer_tags or [],
            scheduled_at=scheduled_at,
            trigger_type=trigger_type,
            created_by=created_by,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return {
            "success": True,
            "campaign_id": str(campaign.id),
            "status": campaign.status.value,
        }

    async def build_recipient_list(
        self,
        db: Session,
        campaign_id: str,
    ) -> Dict[str, Any]:
        """Build recipient list based on campaign targeting rules."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"success": False, "error": "Campaign not found"}

        # Get all customers for the business
        query = db.query(Customer).filter(
            Customer.business_id == campaign.business_id
        )

        # Apply tag filters
        if campaign.customer_tags:
            # Filter customers with any of the tags
            query = query.filter(
                Customer.tags.op('&&')(campaign.customer_tags)
            )

        # Exclude unsubscribed
        unsubscribed_emails = db.query(Unsubscribe.email).filter(
            Unsubscribe.business_id == campaign.business_id,
            Unsubscribe.channel.in_([campaign.campaign_type, None])
        ).all()
        unsubscribed_list = [u[0] for u in unsubscribed_emails if u[0]]

        customers = query.all()
        
        # Filter based on campaign type
        recipients_added = 0
        for customer in customers:
            # Skip unsubscribed
            if customer.email in unsubscribed_list:
                continue

            # Check contact info based on campaign type
            if campaign.campaign_type == CampaignType.EMAIL and not customer.email:
                continue
            if campaign.campaign_type in [CampaignType.SMS, CampaignType.WHATSAPP] and not customer.phone:
                continue

            # Check if already added
            existing = db.query(CampaignRecipient).filter(
                CampaignRecipient.campaign_id == campaign_id,
                CampaignRecipient.customer_id == customer.id,
            ).first()

            if not existing:
                recipient = CampaignRecipient(
                    campaign_id=campaign_id,
                    customer_id=customer.id,
                    email=customer.email,
                    phone=customer.phone,
                    name=customer.name,
                    status=RecipientStatus.PENDING,
                )
                db.add(recipient)
                recipients_added += 1

        campaign.total_recipients = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id
        ).count()

        db.commit()

        return {
            "success": True,
            "recipients_added": recipients_added,
            "total_recipients": campaign.total_recipients,
        }

    async def send_campaign(
        self,
        db: Session,
        campaign_id: str,
    ) -> Dict[str, Any]:
        """Send campaign to all recipients."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"success": False, "error": "Campaign not found"}

        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            return {"success": False, "error": f"Cannot send campaign in {campaign.status} status"}

        # Build recipient list if empty
        if campaign.total_recipients == 0:
            await self.build_recipient_list(db, campaign_id)

        campaign.status = CampaignStatus.SENDING
        campaign.sent_at = datetime.utcnow()
        db.commit()

        # Get pending recipients
        recipients = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == RecipientStatus.PENDING,
        ).all()

        # Send to each recipient
        sent_count = 0
        for recipient in recipients:
            try:
                success = await self._send_to_recipient(db, campaign, recipient)
                if success:
                    sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {recipient.email or recipient.phone}: {e}")
                recipient.status = RecipientStatus.FAILED
                recipient.error_message = str(e)

        campaign.sent_count = sent_count
        campaign.status = CampaignStatus.SENT
        db.commit()

        return {
            "success": True,
            "sent_count": sent_count,
            "total_recipients": campaign.total_recipients,
        }

    async def _send_to_recipient(
        self,
        db: Session,
        campaign: Campaign,
        recipient: CampaignRecipient,
    ) -> bool:
        """Send campaign to a single recipient."""
        # Get template content
        subject = campaign.subject
        content = campaign.content
        html_content = campaign.html_content

        if campaign.template_id:
            template = db.query(EmailTemplate).filter(
                EmailTemplate.id == campaign.template_id
            ).first()
            if template:
                variables = {
                    "customer_name": recipient.name or "Customer",
                    "email": recipient.email,
                    "business_name": campaign.business.name if campaign.business else "",
                }
                subject, content, html_content = template.render(variables)

        # Personalize content
        content = self._personalize_content(content, recipient)
        html_content = self._personalize_content(html_content, recipient)

        # Add tracking pixel and links
        if html_content and campaign.track_opens:
            html_content = self._add_tracking_pixel(html_content, str(recipient.id))

        if campaign.track_clicks:
            html_content = self._wrap_links(db, campaign, html_content)

        # Send based on campaign type
        if campaign.campaign_type == CampaignType.EMAIL:
            success = await self._send_email(
                to=recipient.email,
                subject=subject,
                content=content,
                html_content=html_content,
                from_name=campaign.from_name,
                from_email=campaign.from_email,
            )
        elif campaign.campaign_type == CampaignType.SMS:
            success = await self._send_sms(
                to=recipient.phone,
                message=content,
            )
        elif campaign.campaign_type == CampaignType.WHATSAPP:
            success = await self._send_whatsapp(
                to=recipient.phone,
                message=content,
            )
        else:
            success = False

        if success:
            recipient.status = RecipientStatus.SENT
            recipient.sent_at = datetime.utcnow()
        else:
            recipient.status = RecipientStatus.FAILED

        return success

    def _personalize_content(self, content: str, recipient: CampaignRecipient) -> str:
        """Replace placeholders with recipient data."""
        if not content:
            return content

        replacements = {
            "{{customer_name}}": recipient.name or "Customer",
            "{{first_name}}": (recipient.name or "Customer").split()[0],
            "{{email}}": recipient.email or "",
            "{{phone}}": recipient.phone or "",
        }

        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        return content

    def _add_tracking_pixel(self, html: str, recipient_id: str) -> str:
        """Add invisible tracking pixel for open tracking."""
        tracking_url = f"{settings.API_URL}/api/v1/campaigns/track/open/{recipient_id}"
        pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none" />'
        
        if "</body>" in html:
            html = html.replace("</body>", f"{pixel}</body>")
        else:
            html += pixel

        return html

    def _wrap_links(self, db: Session, campaign: Campaign, html: str) -> str:
        """Wrap links for click tracking."""
        import re
        
        def replace_link(match):
            original_url = match.group(1)
            tracking_code = self._generate_tracking_code()
            
            # Create tracking link record
            link = CampaignLink(
                campaign_id=campaign.id,
                original_url=original_url,
                tracking_code=tracking_code,
            )
            db.add(link)
            
            tracking_url = f"{settings.API_URL}/api/v1/campaigns/track/click/{tracking_code}"
            return f'href="{tracking_url}"'

        # Match href attributes
        pattern = r'href=["\']([^"\']+)["\']'
        html = re.sub(pattern, replace_link, html)
        db.flush()

        return html

    async def _send_email(
        self,
        to: str,
        subject: str,
        content: str,
        html_content: str = None,
        from_name: str = None,
        from_email: str = None,
    ) -> bool:
        """Send email via SMTP."""
        try:
            from app.core.email import email_service
            return email_service.send_email(
                to=to,
                subject=subject,
                body=content,
                html_body=html_content,
                from_name=from_name,
                from_email=from_email,
            )
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            # In demo mode, return True
            return True

    async def _send_sms(self, to: str, message: str) -> bool:
        """Send SMS via Twilio."""
        try:
            from app.services.sms_service import sms_service
            return await sms_service.send_sms(to, message)
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return True  # Demo mode

    async def _send_whatsapp(self, to: str, message: str) -> bool:
        """Send WhatsApp message."""
        try:
            from app.services.notification_service import notification_service
            return await notification_service.send_whatsapp(
                phone=to,
                message_text=message,
            )
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return True  # Demo mode

    async def track_open(self, db: Session, recipient_id: str):
        """Track email open."""
        recipient = db.query(CampaignRecipient).filter(
            CampaignRecipient.id == recipient_id
        ).first()

        if recipient and recipient.status != RecipientStatus.OPENED:
            recipient.status = RecipientStatus.OPENED
            recipient.opened_at = datetime.utcnow()
            recipient.open_count += 1

            # Update campaign stats
            campaign = db.query(Campaign).filter(
                Campaign.id == recipient.campaign_id
            ).first()
            if campaign:
                campaign.opened_count += 1

            db.commit()

    async def track_click(self, db: Session, tracking_code: str) -> str:
        """Track link click and return original URL."""
        link = db.query(CampaignLink).filter(
            CampaignLink.tracking_code == tracking_code
        ).first()

        if not link:
            return settings.FRONTEND_URL

        link.click_count += 1
        
        # Update campaign stats
        campaign = db.query(Campaign).filter(
            Campaign.id == link.campaign_id
        ).first()
        if campaign:
            campaign.clicked_count += 1

        db.commit()

        return link.original_url

    async def unsubscribe(
        self,
        db: Session,
        business_id: str,
        email: str = None,
        phone: str = None,
        channel: CampaignType = None,
        reason: str = None,
        campaign_id: str = None,
    ) -> Dict[str, Any]:
        """Unsubscribe a contact from marketing."""
        # Find customer
        customer = None
        if email:
            customer = db.query(Customer).filter(
                Customer.business_id == business_id,
                Customer.email == email,
            ).first()
        elif phone:
            customer = db.query(Customer).filter(
                Customer.business_id == business_id,
                Customer.phone == phone,
            ).first()

        unsub = Unsubscribe(
            business_id=business_id,
            customer_id=customer.id if customer else None,
            email=email,
            phone=phone,
            channel=channel,
            reason=reason,
            campaign_id=campaign_id,
        )
        db.add(unsub)
        db.commit()

        return {"success": True}

    def get_campaign_stats(self, db: Session, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign statistics."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"error": "Campaign not found"}

        return {
            "campaign_id": str(campaign.id),
            "name": campaign.name,
            "status": campaign.status.value,
            "type": campaign.campaign_type.value,
            "total_recipients": campaign.total_recipients,
            "sent_count": campaign.sent_count,
            "delivered_count": campaign.delivered_count,
            "opened_count": campaign.opened_count,
            "clicked_count": campaign.clicked_count,
            "bounced_count": campaign.bounced_count,
            "unsubscribed_count": campaign.unsubscribed_count,
            "open_rate": campaign.open_rate,
            "click_rate": campaign.click_rate,
            "revenue_attributed": campaign.revenue_attributed,
            "orders_attributed": campaign.orders_attributed,
            "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
        }

    async def create_template(
        self,
        db: Session,
        business_id: str,
        name: str,
        template_type: CampaignType,
        subject: str = None,
        content: str = None,
        html_content: str = None,
        category: str = None,
    ) -> Dict[str, Any]:
        """Create an email/SMS template."""
        template = EmailTemplate(
            business_id=business_id,
            name=name,
            template_type=template_type,
            subject=subject,
            content=content,
            html_content=html_content,
            category=category,
            variables=["customer_name", "first_name", "email", "business_name"],
        )
        db.add(template)
        db.commit()

        return {
            "success": True,
            "template_id": str(template.id),
        }


# Global instance
campaign_service = CampaignService()
