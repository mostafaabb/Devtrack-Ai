"""
Inventory management models.
Supports stock tracking, movements, suppliers, purchase orders, and alerts.
"""
from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.db.session import Base


class StockMovementType(str, enum.Enum):
    """Type of stock movement."""
    PURCHASE = "purchase"          # Received from supplier
    SALE = "sale"                  # Sold to customer
    ADJUSTMENT = "adjustment"      # Manual adjustment
    TRANSFER = "transfer"          # Transfer between locations
    RETURN = "return"              # Customer return
    DAMAGE = "damage"              # Damaged/expired
    INITIAL = "initial"            # Initial stock count


class PurchaseOrderStatus(str, enum.Enum):
    """Purchase order status."""
    DRAFT = "draft"
    PENDING = "pending"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class AlertType(str, enum.Enum):
    """Inventory alert types."""
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    OVERSTOCK = "overstock"
    EXPIRING_SOON = "expiring_soon"
    REORDER_POINT = "reorder_point"


class Supplier(Base):
    """
    Supplier/vendor model for inventory sourcing.
    """
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)

    # Basic info
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    
    # Contact
    contact_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Payment terms
    payment_terms = Column(String(100), nullable=True)  # Net 30, COD, etc.
    currency = Column(String(10), default="USD")
    
    # Performance tracking
    lead_time_days = Column(Integer, default=7)
    rating = Column(Float, nullable=True)  # 1-5 rating
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="suppliers")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    products = relationship("SupplierProduct", back_populates="supplier")

    def __repr__(self):
        return f"<Supplier {self.name}>"


class SupplierProduct(Base):
    """
    Links suppliers to products with pricing.
    """
    __tablename__ = "supplier_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Supplier-specific info
    supplier_sku = Column(String(100), nullable=True)
    cost_price = Column(Float, nullable=False)
    min_order_quantity = Column(Integer, default=1)
    
    # Is this the primary supplier for this product?
    is_primary = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    product = relationship("Product", backref="supplier_links")

    def __repr__(self):
        return f"<SupplierProduct {self.supplier_id} - {self.product_id}>"


class ProductInventory(Base):
    """
    Inventory settings per product (extends Product model).
    Tracks reorder points, safety stock, and location-specific inventory.
    """
    __tablename__ = "product_inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, unique=True)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    
    # Stock levels
    quantity_on_hand = Column(Integer, default=0)
    quantity_reserved = Column(Integer, default=0)  # Reserved for orders
    quantity_available = Column(Integer, default=0)  # on_hand - reserved
    
    # Reorder settings
    reorder_point = Column(Integer, default=10)  # Alert when stock falls below
    reorder_quantity = Column(Integer, default=50)  # How much to reorder
    safety_stock = Column(Integer, default=5)  # Minimum to keep
    max_stock = Column(Integer, nullable=True)  # Maximum stock level
    
    # Cost tracking
    cost_price = Column(Float, default=0)  # Average cost
    last_cost_price = Column(Float, nullable=True)  # Last purchase cost
    
    # Tracking
    last_counted_at = Column(DateTime, nullable=True)
    last_restocked_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", backref="inventory_settings")

    def __repr__(self):
        return f"<ProductInventory {self.product_id} - {self.quantity_on_hand} units>"

    @property
    def needs_reorder(self) -> bool:
        return self.quantity_available <= self.reorder_point


class StockMovement(Base):
    """
    Tracks all inventory movements.
    Provides full audit trail for stock changes.
    """
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    
    # Movement details
    movement_type = Column(SQLEnum(StockMovementType), nullable=False)
    quantity = Column(Integer, nullable=False)  # Positive for in, negative for out
    
    # Stock levels after movement
    quantity_before = Column(Integer, nullable=False)
    quantity_after = Column(Integer, nullable=False)
    
    # Cost tracking
    unit_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    
    # Reference to source
    reference_type = Column(String(50), nullable=True)  # order, purchase_order, adjustment
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Transfer details
    from_location_id = Column(UUID(as_uuid=True), nullable=True)
    to_location_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Notes
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Who made the change
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="stock_movements")
    product = relationship("Product", backref="stock_movements")

    def __repr__(self):
        return f"<StockMovement {self.movement_type} - {self.quantity}>"


class PurchaseOrder(Base):
    """
    Purchase orders for restocking inventory.
    """
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    
    # Order details
    po_number = Column(String(50), unique=True, nullable=False)
    status = Column(SQLEnum(PurchaseOrderStatus), default=PurchaseOrderStatus.DRAFT)
    
    # Financials
    subtotal = Column(Float, default=0)
    tax = Column(Float, default=0)
    shipping = Column(Float, default=0)
    total = Column(Float, default=0)
    currency = Column(String(10), default="USD")
    
    # Dates
    order_date = Column(DateTime, nullable=True)
    expected_date = Column(DateTime, nullable=True)
    received_date = Column(DateTime, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Created by
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PurchaseOrder {self.po_number} - {self.status}>"


class PurchaseOrderItem(Base):
    """
    Individual items in a purchase order.
    """
    __tablename__ = "purchase_order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Item details
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    unit_cost = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", backref="purchase_order_items")

    def __repr__(self):
        return f"<PurchaseOrderItem {self.product_id} x{self.quantity_ordered}>"


class InventoryAlert(Base):
    """
    Inventory alerts for low stock, reorder points, etc.
    """
    __tablename__ = "inventory_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    
    # Alert details
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    message = Column(Text, nullable=False)
    current_quantity = Column(Integer, nullable=False)
    threshold_quantity = Column(Integer, nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    business = relationship("Business", backref="inventory_alerts")
    product = relationship("Product", backref="inventory_alerts")

    def __repr__(self):
        return f"<InventoryAlert {self.alert_type} - {self.product_id}>"
