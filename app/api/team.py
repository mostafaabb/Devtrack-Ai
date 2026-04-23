"""
Team Management API endpoints.
Handles roles, permissions, invitations, and activity logs.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.team_service import team_service, DEFAULT_PERMISSIONS
from app.models.team import (
    Role, Permission, TeamMember, TeamInvite, ActivityLog, Location,
    RoleType, InviteStatus, ActivityAction
)


router = APIRouter(prefix="/team", tags=["Team Management"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str]


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class InviteCreate(BaseModel):
    email: EmailStr
    role_id: str
    name: Optional[str] = None
    message: Optional[str] = None


class InviteAccept(BaseModel):
    invite_token: str


class MemberUpdate(BaseModel):
    role_id: Optional[str] = None
    display_name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    location_id: Optional[str] = None
    is_active: Optional[bool] = None


class LocationCreate(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_primary: bool = False
    operating_hours: Optional[dict] = None


# ═══════════════════════════════════════════════════════════════════
# Permissions
# ═══════════════════════════════════════════════════════════════════

@router.get("/permissions")
def list_permissions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all available permissions."""
    # Group by category
    categories = {}
    for perm in DEFAULT_PERMISSIONS:
        cat = perm["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "code": perm["code"],
            "name": perm["name"],
        })
    
    return categories


@router.get("/my-permissions")
def get_my_permissions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's permissions."""
    permissions = team_service.get_user_permissions(
        db,
        str(current_user["user_id"]),
        str(current_user["business_id"]),
    )
    
    return {"permissions": permissions}


# ═══════════════════════════════════════════════════════════════════
# Roles
# ═══════════════════════════════════════════════════════════════════

@router.get("/roles")
async def list_roles(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all roles for the business."""
    # Ensure default roles exist
    await team_service.create_default_roles(db, str(current_user["business_id"]))
    
    roles = db.query(Role).filter(
        (Role.business_id == current_user["business_id"]) |
        (Role.business_id == None)  # System roles
    ).order_by(Role.role_type).all()
    
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "role_type": r.role_type.value,
            "permissions": r.permissions,
            "is_system": r.is_system,
            "member_count": len(r.members) if r.members else 0,
        }
        for r in roles
    ]


@router.post("/roles")
async def create_role(
    data: RoleCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a custom role."""
    result = await team_service.create_role(
        db=db,
        business_id=str(current_user["business_id"]),
        name=data.name,
        permissions=data.permissions,
        description=data.description,
    )
    
    return result


@router.put("/roles/{role_id}")
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a role."""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.business_id == current_user["business_id"],
    ).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.is_system and role.role_type == RoleType.OWNER:
        raise HTTPException(status_code=403, detail="Cannot modify owner role")
    
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.permissions is not None:
        role.permissions = data.permissions
    
    role.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a custom role."""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.business_id == current_user["business_id"],
    ).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system roles")
    
    if role.members:
        raise HTTPException(status_code=400, detail="Cannot delete role with members")
    
    db.delete(role)
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Team Members
# ═══════════════════════════════════════════════════════════════════

@router.get("/members")
def list_members(
    include_inactive: bool = False,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all team members."""
    return team_service.get_team_members(
        db,
        str(current_user["business_id"]),
        include_inactive,
    )


@router.get("/members/{member_id}")
def get_member(
    member_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get team member details."""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.business_id == current_user["business_id"],
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {
        "id": str(member.id),
        "user_id": str(member.user_id),
        "display_name": member.display_name,
        "email": member.user.email if member.user else None,
        "title": member.title,
        "department": member.department,
        "role_id": str(member.role_id),
        "role_name": member.role.name if member.role else None,
        "location_id": str(member.location_id) if member.location_id else None,
        "permissions": team_service.get_user_permissions(
            db, str(member.user_id), str(current_user["business_id"])
        ),
        "is_active": member.is_active,
        "joined_at": member.joined_at.isoformat(),
        "last_active_at": member.last_active_at.isoformat() if member.last_active_at else None,
    }


@router.put("/members/{member_id}")
def update_member(
    member_id: UUID,
    data: MemberUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update team member."""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.business_id == current_user["business_id"],
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if data.role_id is not None:
        member.role_id = data.role_id
    if data.display_name is not None:
        member.display_name = data.display_name
    if data.title is not None:
        member.title = data.title
    if data.department is not None:
        member.department = data.department
    if data.location_id is not None:
        member.location_id = data.location_id
    if data.is_active is not None:
        member.is_active = data.is_active
    
    member.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.delete("/members/{member_id}")
def remove_member(
    member_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a team member."""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.business_id == current_user["business_id"],
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Prevent removing yourself
    if str(member.user_id) == str(current_user["user_id"]):
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    
    db.delete(member)
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Invitations
# ═══════════════════════════════════════════════════════════════════

@router.get("/invites")
def list_invites(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List team invitations."""
    query = db.query(TeamInvite).filter(
        TeamInvite.business_id == current_user["business_id"]
    )
    
    if status:
        try:
            query = query.filter(TeamInvite.status == InviteStatus(status))
        except ValueError:
            pass
    
    invites = query.order_by(TeamInvite.created_at.desc()).all()
    
    return [
        {
            "id": str(i.id),
            "email": i.email,
            "name": i.name,
            "role_id": str(i.role_id),
            "role_name": i.role.name if i.role else None,
            "status": i.status.value,
            "expires_at": i.expires_at.isoformat(),
            "is_expired": i.is_expired,
            "created_at": i.created_at.isoformat(),
        }
        for i in invites
    ]


@router.post("/invites")
async def send_invite(
    data: InviteCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send team invitation."""
    result = await team_service.invite_member(
        db=db,
        business_id=str(current_user["business_id"]),
        email=data.email,
        role_id=data.role_id,
        name=data.name,
        message=data.message,
        invited_by=str(current_user["user_id"]),
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/invites/accept")
async def accept_invite(
    data: InviteAccept,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept a team invitation."""
    result = await team_service.accept_invite(
        db=db,
        invite_token=data.invite_token,
        user_id=str(current_user["user_id"]),
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete("/invites/{invite_id}")
def cancel_invite(
    invite_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a pending invitation."""
    invite = db.query(TeamInvite).filter(
        TeamInvite.id == invite_id,
        TeamInvite.business_id == current_user["business_id"],
        TeamInvite.status == InviteStatus.PENDING,
    ).first()
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    invite.status = InviteStatus.CANCELLED
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Activity Logs
# ═══════════════════════════════════════════════════════════════════

@router.get("/activity")
def get_activity_logs(
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get activity logs."""
    action_enum = None
    if action:
        try:
            action_enum = ActivityAction(action)
        except ValueError:
            pass
    
    logs = team_service.get_activity_logs(
        db=db,
        business_id=str(current_user["business_id"]),
        user_id=user_id,
        entity_type=entity_type,
        action=action_enum,
        limit=limit,
        offset=offset,
    )
    
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "user_name": log.user.full_name if log.user else None,
            "action": log.action.value,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "description": log.description,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


# ═══════════════════════════════════════════════════════════════════
# Locations
# ═══════════════════════════════════════════════════════════════════

@router.get("/locations")
def list_locations(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all business locations."""
    query = db.query(Location).filter(
        Location.business_id == current_user["business_id"]
    )
    
    if active_only:
        query = query.filter(Location.is_active == True)
    
    locations = query.order_by(Location.is_primary.desc(), Location.name).all()
    
    return [
        {
            "id": str(loc.id),
            "name": loc.name,
            "code": loc.code,
            "address": loc.address,
            "city": loc.city,
            "country": loc.country,
            "phone": loc.phone,
            "email": loc.email,
            "is_primary": loc.is_primary,
            "is_active": loc.is_active,
            "operating_hours": loc.operating_hours,
        }
        for loc in locations
    ]


@router.post("/locations")
async def create_location(
    data: LocationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new location."""
    result = await team_service.create_location(
        db=db,
        business_id=str(current_user["business_id"]),
        name=data.name,
        address=data.address,
        city=data.city,
        country=data.country,
        phone=data.phone,
        email=data.email,
        is_primary=data.is_primary,
        operating_hours=data.operating_hours,
    )
    
    return result


@router.put("/locations/{location_id}")
def update_location(
    location_id: UUID,
    data: LocationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a location."""
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.business_id == current_user["business_id"],
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    location.name = data.name
    location.address = data.address
    location.city = data.city
    location.country = data.country
    location.phone = data.phone
    location.email = data.email
    location.operating_hours = data.operating_hours
    
    if data.is_primary and not location.is_primary:
        # Unset other primary locations
        db.query(Location).filter(
            Location.business_id == current_user["business_id"],
            Location.is_primary == True,
        ).update({"is_primary": False})
        location.is_primary = True
    
    location.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


@router.delete("/locations/{location_id}")
def delete_location(
    location_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a location."""
    location = db.query(Location).filter(
        Location.id == location_id,
        Location.business_id == current_user["business_id"],
    ).first()
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    if location.is_primary:
        raise HTTPException(status_code=400, detail="Cannot delete primary location")
    
    db.delete(location)
    db.commit()
    
    return {"success": True}
