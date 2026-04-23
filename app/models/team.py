"""
Team and permission models.
Supports roles, permissions, team invitations, and activity logging.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class RoleType(str, enum.Enum):
    """Built-in role types."""
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"
    CUSTOM = "custom"


class InviteStatus(str, enum.Enum):
    """Team invitation status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActivityAction(str, enum.Enum):
    """Activity log action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"


class Permission(Base):
    """
    Individual permission definition.
    """
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Permission details
    code = Column(String(100), unique=True, nullable=False)  # e.g., "orders.create"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Grouping
    category = Column(String(100), nullable=False)  # orders, customers, analytics
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Permission {self.code}>"


class Role(Base):
    """
    Role definition with associated permissions.
    """
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=True)  # Null for system roles
    
    # Role details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    role_type = Column(SQLEnum(RoleType), default=RoleType.CUSTOM)
    
    # Permissions (list of permission codes)
    permissions = Column(JSON, default=list)
    
    # System role flag (cannot be deleted/modified)
    is_system = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="roles")
    members = relationship("TeamMember", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"

    def has_permission(self, permission_code: str) -> bool:
        """Check if role has a specific permission."""
        # Owner has all permissions
        if self.role_type == RoleType.OWNER:
            return True
        return permission_code in self.permissions


class TeamMember(Base):
    """
    Links users to businesses with roles.
    Enables multi-business membership.
    """
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    
    # Member info
    display_name = Column(String(255), nullable=True)  # Override user's name
    title = Column(String(100), nullable=True)  # Job title
    department = Column(String(100), nullable=True)
    
    # Location assignment
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    
    # Work hours (JSON) - for scheduling
    work_schedule = Column(JSON, default=dict)
    
    # Permissions override (additional permissions beyond role)
    extra_permissions = Column(JSON, default=list)
    restricted_permissions = Column(JSON, default=list)  # Deny specific permissions
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", backref="team_members")
    user = relationship("User", backref="team_memberships")
    role = relationship("Role", back_populates="members")

    def __repr__(self):
        return f"<TeamMember {self.user_id} @ {self.business_id}>"

    def has_permission(self, permission_code: str) -> bool:
        """Check if member has a specific permission."""
        # Check restricted first
        if permission_code in self.restricted_permissions:
            return False
        # Check extra permissions
        if permission_code in self.extra_permissions:
            return True
        # Check role permissions
        return self.role.has_permission(permission_code) if self.role else False


class TeamInvite(Base):
    """
    Team invitations for new members.
    """
    __tablename__ = "team_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    
    # Invitee info
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    
    # Invitation details
    invite_token = Column(String(255), unique=True, nullable=False)
    message = Column(Text, nullable=True)
    
    # Status
    status = Column(SQLEnum(InviteStatus), default=InviteStatus.PENDING)
    
    # Validity
    expires_at = Column(DateTime, nullable=False)
    
    # Who sent the invite
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)

    # Relationships
    business = relationship("Business", backref="invites")
    role = relationship("Role", backref="invites")
    inviter = relationship("User", backref="sent_invites")

    def __repr__(self):
        return f"<TeamInvite {self.email} - {self.status}>"

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class ActivityLog(Base):
    """
    Audit trail for all user actions.
    """
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Action details
    action = Column(SQLEnum(ActivityAction), nullable=False)
    entity_type = Column(String(50), nullable=False)  # order, customer, product
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Change tracking
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Request info
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="activity_logs")
    user = relationship("User", backref="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.action} {self.entity_type}>"


class Location(Base):
    """
    Business locations/branches.
    Enables multi-location management.
    """
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    
    # Location details
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)  # Internal code
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # Coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Contact
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Operating hours (JSON)
    operating_hours = Column(JSON, default=dict)
    
    # Settings
    timezone = Column(String(50), default="UTC")
    currency = Column(String(10), default="USD")
    
    # Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="locations")

    def __repr__(self):
        return f"<Location {self.name}>"
