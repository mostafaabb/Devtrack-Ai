"""
Marketing Campaigns API endpoints.
Handles email/SMS campaigns, templates, and tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.campaign_service import campaign_service
from app.models.campaign import (
    Campaign, EmailTemplate, CampaignRecipient,
    CampaignType, CampaignStatus, TriggerType
)


router = APIRouter(prefix="/campaigns", tags=["Marketing Campaigns"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class CampaignCreate(BaseModel):
    name: str
    campaign_type: str = "email"
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    template_id: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    segment_rules: Optional[dict] = None
    customer_tags: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    trigger_type: str = "manual"


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class TemplateCreate(BaseModel):
    name: str
    template_type: str = "email"
    subject: Optional[str] = None
    content: Optional[str] = None
    html_content: Optional[str] = None
    category: Optional[str] = None


class UnsubscribeRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: Optional[str] = None
    reason: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# Campaign Endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/")
def list_campaigns(
    status: Optional[str] = None,
    campaign_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all campaigns."""
    query = db.query(Campaign).filter(
        Campaign.business_id == current_user["business_id"]
    )
    
    if status:
        try:
            query = query.filter(Campaign.status == CampaignStatus(status))
        except ValueError:
            pass
    
    if campaign_type:
        try:
            query = query.filter(Campaign.campaign_type == CampaignType(campaign_type))
        except ValueError:
            pass
    
    campaigns = query.order_by(Campaign.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "campaign_type": c.campaign_type.value,
            "status": c.status.value,
            "subject": c.subject,
            "total_recipients": c.total_recipients,
            "sent_count": c.sent_count,
            "opened_count": c.opened_count,
            "clicked_count": c.clicked_count,
            "open_rate": c.open_rate,
            "click_rate": c.click_rate,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "sent_at": c.sent_at.isoformat() if c.sent_at else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in campaigns
    ]


@router.post("/")
async def create_campaign(
    data: CampaignCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new campaign."""
    try:
        campaign_type = CampaignType(data.campaign_type)
    except ValueError:
        campaign_type = CampaignType.EMAIL
    
    try:
        trigger_type = TriggerType(data.trigger_type)
    except ValueError:
        trigger_type = TriggerType.MANUAL
    
    result = await campaign_service.create_campaign(
        db=db,
        business_id=str(current_user["business_id"]),
        name=data.name,
        campaign_type=campaign_type,
        subject=data.subject,
        content=data.content,
        html_content=data.html_content,
        template_id=data.template_id,
        from_name=data.from_name,
        from_email=data.from_email,
        segment_rules=data.segment_rules,
        customer_tags=data.customer_tags,
        scheduled_at=data.scheduled_at,
        trigger_type=trigger_type,
        created_by=str(current_user["user_id"]),
    )
    
    return result


@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get campaign details."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.business_id == current_user["business_id"],
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "description": campaign.description,
        "campaign_type": campaign.campaign_type.value,
        "status": campaign.status.value,
        "subject": campaign.subject,
        "content": campaign.content,
        "html_content": campaign.html_content,
        "template_id": str(campaign.template_id) if campaign.template_id else None,
        "from_name": campaign.from_name,
        "from_email": campaign.from_email,
        "segment_rules": campaign.segment_rules,
        "customer_tags": campaign.customer_tags,
        "trigger_type": campaign.trigger_type.value,
        "scheduled_at": campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
        "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
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
        "created_at": campaign.created_at.isoformat(),
    }


@router.put("/{campaign_id}")
def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a campaign (only draft campaigns can be updated)."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.business_id == current_user["business_id"],
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only update draft campaigns")
    
    if data.name is not None:
        campaign.name = data.name
    if data.subject is not None:
        campaign.subject = data.subject
    if data.content is not None:
        campaign.content = data.content
    if data.html_content is not None:
        campaign.html_content = data.html_content
    if data.from_name is not None:
        campaign.from_name = data.from_name
    if data.from_email is not None:
        campaign.from_email = data.from_email
    if data.scheduled_at is not None:
        campaign.scheduled_at = data.scheduled_at
    
    campaign.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.post("/{campaign_id}/build-recipients")
async def build_recipient_list(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Build recipient list for a campaign."""
    result = await campaign_service.build_recipient_list(db, str(campaign_id))
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a campaign to all recipients."""
    result = await campaign_service.send_campaign(db, str(campaign_id))
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{campaign_id}/schedule")
def schedule_campaign(
    campaign_id: UUID,
    scheduled_at: datetime,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule a campaign for later sending."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.business_id == current_user["business_id"],
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status not in [CampaignStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Can only schedule draft campaigns")
    
    campaign.scheduled_at = scheduled_at
    campaign.status = CampaignStatus.SCHEDULED
    db.commit()
    
    return {"success": True, "scheduled_at": scheduled_at.isoformat()}


@router.get("/{campaign_id}/stats")
def get_campaign_stats(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed campaign statistics."""
    return campaign_service.get_campaign_stats(db, str(campaign_id))


@router.get("/{campaign_id}/recipients")
def get_campaign_recipients(
    campaign_id: UUID,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get campaign recipients."""
    query = db.query(CampaignRecipient).filter(
        CampaignRecipient.campaign_id == campaign_id
    )
    
    if status:
        from app.models.campaign import RecipientStatus
        try:
            query = query.filter(CampaignRecipient.status == RecipientStatus(status))
        except ValueError:
            pass
    
    recipients = query.offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(r.id),
            "email": r.email,
            "phone": r.phone,
            "name": r.name,
            "status": r.status.value,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "clicked_at": r.clicked_at.isoformat() if r.clicked_at else None,
            "open_count": r.open_count,
            "click_count": r.click_count,
        }
        for r in recipients
    ]


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.business_id == current_user["business_id"],
    ).first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status == CampaignStatus.SENDING:
        raise HTTPException(status_code=400, detail="Cannot delete campaign while sending")
    
    db.delete(campaign)
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Tracking Endpoints (Public)
# ═══════════════════════════════════════════════════════════════════

@router.get("/track/open/{recipient_id}")
async def track_open(
    recipient_id: UUID,
    db: Session = Depends(get_db),
):
    """Track email open (called by tracking pixel)."""
    await campaign_service.track_open(db, str(recipient_id))
    
    # Return a 1x1 transparent GIF
    gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return Response(content=gif, media_type="image/gif")


@router.get("/track/click/{tracking_code}")
async def track_click(
    tracking_code: str,
    db: Session = Depends(get_db),
):
    """Track link click and redirect."""
    from fastapi.responses import RedirectResponse
    
    original_url = await campaign_service.track_click(db, tracking_code)
    return RedirectResponse(url=original_url)


# ═══════════════════════════════════════════════════════════════════
# Templates
# ═══════════════════════════════════════════════════════════════════

@router.get("/templates")
def list_templates(
    template_type: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List email/SMS templates."""
    query = db.query(EmailTemplate).filter(
        EmailTemplate.business_id == current_user["business_id"],
        EmailTemplate.is_active == True,
    )
    
    if template_type:
        try:
            query = query.filter(EmailTemplate.template_type == CampaignType(template_type))
        except ValueError:
            pass
    
    if category:
        query = query.filter(EmailTemplate.category == category)
    
    templates = query.order_by(EmailTemplate.name).all()
    
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "template_type": t.template_type.value,
            "subject": t.subject,
            "category": t.category,
            "variables": t.variables,
        }
        for t in templates
    ]


@router.post("/templates")
async def create_template(
    data: TemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new template."""
    try:
        template_type = CampaignType(data.template_type)
    except ValueError:
        template_type = CampaignType.EMAIL
    
    result = await campaign_service.create_template(
        db=db,
        business_id=str(current_user["business_id"]),
        name=data.name,
        template_type=template_type,
        subject=data.subject,
        content=data.content,
        html_content=data.html_content,
        category=data.category,
    )
    
    return result


@router.get("/templates/{template_id}")
def get_template(
    template_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get template details."""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id,
        EmailTemplate.business_id == current_user["business_id"],
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "template_type": template.template_type.value,
        "subject": template.subject,
        "content": template.content,
        "html_content": template.html_content,
        "category": template.category,
        "variables": template.variables,
    }


# ═══════════════════════════════════════════════════════════════════
# Unsubscribe
# ═══════════════════════════════════════════════════════════════════

@router.post("/unsubscribe")
async def unsubscribe(
    data: UnsubscribeRequest,
    business_id: str,
    campaign_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Unsubscribe from marketing (public endpoint)."""
    channel = None
    if data.channel:
        try:
            channel = CampaignType(data.channel)
        except ValueError:
            pass
    
    result = await campaign_service.unsubscribe(
        db=db,
        business_id=business_id,
        email=data.email,
        phone=data.phone,
        channel=channel,
        reason=data.reason,
        campaign_id=campaign_id,
    )
    
    return result
