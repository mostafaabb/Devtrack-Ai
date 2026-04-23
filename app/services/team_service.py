"""
Team Service - Role-based access control and team management.
Handles roles, permissions, invitations, and activity logging.
"""
import logging
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.team import (
    Role, Permission, TeamMember, TeamInvite, ActivityLog, Location,
    RoleType, InviteStatus, ActivityAction
)
from app.models.user import User

logger = logging.getLogger("devtrack.team")


# Default permission definitions
DEFAULT_PERMISSIONS = [
    # Dashboard
    {"code": "dashboard.view", "name": "View Dashboard", "category": "dashboard"},
    
    # Customers
    {"code": "customers.view", "name": "View Customers", "category": "customers"},
    {"code": "customers.create", "name": "Create Customers", "category": "customers"},
    {"code": "customers.edit", "name": "Edit Customers", "category": "customers"},
    {"code": "customers.delete", "name": "Delete Customers", "category": "customers"},
    {"code": "customers.export", "name": "Export Customers", "category": "customers"},
    
    # Orders
    {"code": "orders.view", "name": "View Orders", "category": "orders"},
    {"code": "orders.create", "name": "Create Orders", "category": "orders"},
    {"code": "orders.edit", "name": "Edit Orders", "category": "orders"},
    {"code": "orders.delete", "name": "Delete Orders", "category": "orders"},
    {"code": "orders.refund", "name": "Process Refunds", "category": "orders"},
    
    # Bookings
    {"code": "bookings.view", "name": "View Bookings", "category": "bookings"},
    {"code": "bookings.create", "name": "Create Bookings", "category": "bookings"},
    {"code": "bookings.edit", "name": "Edit Bookings", "category": "bookings"},
    {"code": "bookings.delete", "name": "Delete Bookings", "category": "bookings"},
    
    # Products
    {"code": "products.view", "name": "View Products", "category": "products"},
    {"code": "products.create", "name": "Create Products", "category": "products"},
    {"code": "products.edit", "name": "Edit Products", "category": "products"},
    {"code": "products.delete", "name": "Delete Products", "category": "products"},
    
    # Inventory
    {"code": "inventory.view", "name": "View Inventory", "category": "inventory"},
    {"code": "inventory.adjust", "name": "Adjust Stock", "category": "inventory"},
    {"code": "inventory.purchase_orders", "name": "Manage Purchase Orders", "category": "inventory"},
    
    # Conversations
    {"code": "conversations.view", "name": "View Conversations", "category": "conversations"},
    {"code": "conversations.reply", "name": "Reply to Conversations", "category": "conversations"},
    {"code": "conversations.assign", "name": "Assign Conversations", "category": "conversations"},
    
    # Analytics
    {"code": "analytics.view", "name": "View Analytics", "category": "analytics"},
    {"code": "analytics.export", "name": "Export Reports", "category": "analytics"},
    
    # Marketing
    {"code": "campaigns.view", "name": "View Campaigns", "category": "marketing"},
    {"code": "campaigns.create", "name": "Create Campaigns", "category": "marketing"},
    {"code": "campaigns.send", "name": "Send Campaigns", "category": "marketing"},
    
    # Settings
    {"code": "settings.view", "name": "View Settings", "category": "settings"},
    {"code": "settings.edit", "name": "Edit Settings", "category": "settings"},
    {"code": "settings.billing", "name": "Manage Billing", "category": "settings"},
    
    # Team
    {"code": "team.view", "name": "View Team", "category": "team"},
    {"code": "team.invite", "name": "Invite Members", "category": "team"},
    {"code": "team.manage", "name": "Manage Team", "category": "team"},
    {"code": "team.roles", "name": "Manage Roles", "category": "team"},
]

# Default role permission sets
ROLE_PERMISSIONS = {
    RoleType.OWNER: ["*"],  # All permissions
    RoleType.ADMIN: [
        "dashboard.view", "customers.*", "orders.*", "bookings.*",
        "products.*", "inventory.*", "conversations.*", "analytics.*",
        "campaigns.*", "settings.view", "settings.edit", "team.*"
    ],
    RoleType.MANAGER: [
        "dashboard.view", "customers.view", "customers.create", "customers.edit",
        "orders.*", "bookings.*", "products.view", "products.edit",
        "inventory.view", "inventory.adjust", "conversations.*",
        "analytics.view", "campaigns.view", "team.view"
    ],
    RoleType.STAFF: [
        "dashboard.view", "customers.view", "orders.view", "orders.create", "orders.edit",
        "bookings.view", "bookings.create", "bookings.edit",
        "products.view", "inventory.view", "conversations.view", "conversations.reply"
    ],
    RoleType.VIEWER: [
        "dashboard.view", "customers.view", "orders.view",
        "bookings.view", "products.view", "analytics.view"
    ],
}


class TeamService:
    """
    Team management service.
    Handles roles, permissions, invitations, and audit logging.
    """

    async def initialize_permissions(self, db: Session):
        """Initialize default permissions in the database."""
        for perm_data in DEFAULT_PERMISSIONS:
            existing = db.query(Permission).filter(
                Permission.code == perm_data["code"]
            ).first()
            
            if not existing:
                perm = Permission(**perm_data)
                db.add(perm)
        
        db.commit()

    async def create_default_roles(self, db: Session, business_id: str):
        """Create default roles for a business."""
        for role_type in [RoleType.ADMIN, RoleType.MANAGER, RoleType.STAFF, RoleType.VIEWER]:
            existing = db.query(Role).filter(
                Role.business_id == business_id,
                Role.role_type == role_type,
            ).first()

            if not existing:
                permissions = self._expand_permissions(ROLE_PERMISSIONS.get(role_type, []))
                role = Role(
                    business_id=business_id,
                    name=role_type.value.title(),
                    role_type=role_type,
                    permissions=permissions,
                    is_system=True,
                )
                db.add(role)

        db.commit()

    def _expand_permissions(self, permission_patterns: List[str]) -> List[str]:
        """Expand permission patterns like 'orders.*' to actual permissions."""
        expanded = []
        all_permissions = [p["code"] for p in DEFAULT_PERMISSIONS]

        for pattern in permission_patterns:
            if pattern == "*":
                return all_permissions
            elif pattern.endswith(".*"):
                category = pattern[:-2]
                expanded.extend([p for p in all_permissions if p.startswith(f"{category}.")])
            else:
                expanded.append(pattern)

        return list(set(expanded))

    async def create_role(
        self,
        db: Session,
        business_id: str,
        name: str,
        permissions: List[str],
        description: str = None,
    ) -> Dict[str, Any]:
        """Create a custom role."""
        role = Role(
            business_id=business_id,
            name=name,
            description=description,
            role_type=RoleType.CUSTOM,
            permissions=permissions,
        )
        db.add(role)
        db.commit()

        return {
            "success": True,
            "role_id": str(role.id),
        }

    async def update_role_permissions(
        self,
        db: Session,
        role_id: str,
        permissions: List[str],
    ) -> Dict[str, Any]:
        """Update role permissions."""
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            return {"success": False, "error": "Role not found"}

        if role.is_system and role.role_type == RoleType.OWNER:
            return {"success": False, "error": "Cannot modify owner role"}

        role.permissions = permissions
        role.updated_at = datetime.utcnow()
        db.commit()

        return {"success": True}

    async def add_team_member(
        self,
        db: Session,
        business_id: str,
        user_id: str,
        role_id: str,
        display_name: str = None,
        title: str = None,
        department: str = None,
        location_id: str = None,
    ) -> Dict[str, Any]:
        """Add a user as team member."""
        # Check if already a member
        existing = db.query(TeamMember).filter(
            TeamMember.business_id == business_id,
            TeamMember.user_id == user_id,
        ).first()

        if existing:
            return {"success": False, "error": "User is already a team member"}

        member = TeamMember(
            business_id=business_id,
            user_id=user_id,
            role_id=role_id,
            display_name=display_name,
            title=title,
            department=department,
            location_id=location_id,
        )
        db.add(member)
        db.commit()

        return {
            "success": True,
            "member_id": str(member.id),
        }

    async def invite_member(
        self,
        db: Session,
        business_id: str,
        email: str,
        role_id: str,
        name: str = None,
        message: str = None,
        invited_by: str = None,
    ) -> Dict[str, Any]:
        """Send team invitation."""
        # Check for existing pending invite
        existing = db.query(TeamInvite).filter(
            TeamInvite.business_id == business_id,
            TeamInvite.email == email,
            TeamInvite.status == InviteStatus.PENDING,
        ).first()

        if existing:
            return {"success": False, "error": "Invitation already sent to this email"}

        # Check if user already exists and is a member
        user = db.query(User).filter(User.email == email).first()
        if user:
            existing_member = db.query(TeamMember).filter(
                TeamMember.business_id == business_id,
                TeamMember.user_id == user.id,
            ).first()
            if existing_member:
                return {"success": False, "error": "User is already a team member"}

        invite = TeamInvite(
            business_id=business_id,
            role_id=role_id,
            email=email,
            name=name,
            message=message,
            invite_token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=7),
            invited_by=invited_by,
        )
        db.add(invite)
        db.commit()

        # TODO: Send invitation email
        # await self._send_invitation_email(invite)

        return {
            "success": True,
            "invite_id": str(invite.id),
            "invite_token": invite.invite_token,
        }

    async def accept_invite(
        self,
        db: Session,
        invite_token: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Accept a team invitation."""
        invite = db.query(TeamInvite).filter(
            TeamInvite.invite_token == invite_token,
            TeamInvite.status == InviteStatus.PENDING,
        ).first()

        if not invite:
            return {"success": False, "error": "Invalid or expired invitation"}

        if invite.is_expired:
            invite.status = InviteStatus.EXPIRED
            db.commit()
            return {"success": False, "error": "Invitation has expired"}

        # Add as team member
        result = await self.add_team_member(
            db,
            business_id=str(invite.business_id),
            user_id=user_id,
            role_id=str(invite.role_id),
            display_name=invite.name,
        )

        if result.get("success"):
            invite.status = InviteStatus.ACCEPTED
            invite.responded_at = datetime.utcnow()
            db.commit()

        return result

    def check_permission(
        self,
        db: Session,
        user_id: str,
        business_id: str,
        permission_code: str,
    ) -> bool:
        """Check if user has a specific permission."""
        member = db.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.business_id == business_id,
            TeamMember.is_active == True,
        ).first()

        if not member:
            return False

        return member.has_permission(permission_code)

    def get_user_permissions(
        self,
        db: Session,
        user_id: str,
        business_id: str,
    ) -> List[str]:
        """Get all permissions for a user in a business."""
        member = db.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.business_id == business_id,
            TeamMember.is_active == True,
        ).first()

        if not member:
            return []

        # Get role permissions
        role = member.role
        if not role:
            return []

        # Owner has all permissions
        if role.role_type == RoleType.OWNER:
            return [p["code"] for p in DEFAULT_PERMISSIONS]

        # Combine role permissions with extras, minus restrictions
        permissions = set(role.permissions or [])
        permissions.update(member.extra_permissions or [])
        permissions -= set(member.restricted_permissions or [])

        return list(permissions)

    async def log_activity(
        self,
        db: Session,
        business_id: str,
        user_id: str,
        action: ActivityAction,
        entity_type: str,
        entity_id: str = None,
        description: str = None,
        old_values: Dict = None,
        new_values: Dict = None,
        ip_address: str = None,
        user_agent: str = None,
    ):
        """Log user activity."""
        log = ActivityLog(
            business_id=business_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
        db.commit()

    def get_activity_logs(
        self,
        db: Session,
        business_id: str,
        user_id: str = None,
        entity_type: str = None,
        action: ActivityAction = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ActivityLog]:
        """Get activity logs with filters."""
        query = db.query(ActivityLog).filter(
            ActivityLog.business_id == business_id
        )

        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if entity_type:
            query = query.filter(ActivityLog.entity_type == entity_type)
        if action:
            query = query.filter(ActivityLog.action == action)

        return query.order_by(
            ActivityLog.created_at.desc()
        ).offset(offset).limit(limit).all()

    async def create_location(
        self,
        db: Session,
        business_id: str,
        name: str,
        address: str = None,
        city: str = None,
        country: str = None,
        phone: str = None,
        email: str = None,
        is_primary: bool = False,
        operating_hours: Dict = None,
    ) -> Dict[str, Any]:
        """Create a business location."""
        # If primary, unset other primary locations
        if is_primary:
            db.query(Location).filter(
                Location.business_id == business_id,
                Location.is_primary == True,
            ).update({"is_primary": False})

        location = Location(
            business_id=business_id,
            name=name,
            address=address,
            city=city,
            country=country,
            phone=phone,
            email=email,
            is_primary=is_primary,
            operating_hours=operating_hours or {},
        )
        db.add(location)
        db.commit()

        return {
            "success": True,
            "location_id": str(location.id),
        }

    def get_team_members(
        self,
        db: Session,
        business_id: str,
        include_inactive: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get all team members for a business."""
        query = db.query(TeamMember).filter(
            TeamMember.business_id == business_id
        )

        if not include_inactive:
            query = query.filter(TeamMember.is_active == True)

        members = query.all()

        return [
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "display_name": m.display_name or (m.user.full_name if m.user else None),
                "email": m.user.email if m.user else None,
                "title": m.title,
                "department": m.department,
                "role": m.role.name if m.role else None,
                "role_type": m.role.role_type.value if m.role else None,
                "is_active": m.is_active,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                "last_active_at": m.last_active_at.isoformat() if m.last_active_at else None,
            }
            for m in members
        ]


# Global instance
team_service = TeamService()
