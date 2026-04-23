"""
Inventory API endpoints.
Handles stock management, movements, suppliers, and purchase orders.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user
from app.services.inventory_service import inventory_service
from app.models.inventory import (
    ProductInventory, StockMovement, StockMovementType,
    PurchaseOrder, PurchaseOrderStatus, Supplier, InventoryAlert
)


router = APIRouter(prefix="/inventory", tags=["Inventory"])


# ═══════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════

class StockAdjustment(BaseModel):
    product_id: str
    quantity: int = Field(..., description="Positive for stock in, negative for stock out")
    movement_type: str = "adjustment"
    reason: Optional[str] = None
    unit_cost: Optional[float] = None


class PurchaseOrderItemCreate(BaseModel):
    product_id: str
    quantity: int
    unit_cost: float
    notes: Optional[str] = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    items: List[PurchaseOrderItemCreate]
    notes: Optional[str] = None
    expected_date: Optional[datetime] = None


class ReceiveItemInput(BaseModel):
    item_id: str
    quantity_received: int


class ReceivePurchaseOrder(BaseModel):
    items: List[ReceiveItemInput]


class SupplierCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: int = 7


class InventorySettingsUpdate(BaseModel):
    reorder_point: Optional[int] = None
    reorder_quantity: Optional[int] = None
    safety_stock: Optional[int] = None
    max_stock: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════
# Stock Management
# ═══════════════════════════════════════════════════════════════════

@router.get("/summary")
def get_inventory_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory summary for the business."""
    return inventory_service.get_inventory_summary(
        db, str(current_user["business_id"])
    )


@router.post("/adjust")
async def adjust_stock(
    data: StockAdjustment,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adjust stock for a product."""
    try:
        movement_type = StockMovementType(data.movement_type)
    except ValueError:
        movement_type = StockMovementType.ADJUSTMENT
    
    result = await inventory_service.adjust_stock(
        db=db,
        business_id=str(current_user["business_id"]),
        product_id=data.product_id,
        quantity=data.quantity,
        movement_type=movement_type,
        reason=data.reason,
        unit_cost=data.unit_cost,
        created_by=str(current_user["user_id"]),
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/movements")
def get_stock_movements(
    product_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get stock movement history."""
    mtype = None
    if movement_type:
        try:
            mtype = StockMovementType(movement_type)
        except ValueError:
            pass
    
    movements = inventory_service.get_stock_movements(
        db=db,
        business_id=str(current_user["business_id"]),
        product_id=product_id,
        movement_type=mtype,
        limit=limit,
        offset=offset,
    )
    
    return [
        {
            "id": str(m.id),
            "product_id": str(m.product_id),
            "movement_type": m.movement_type.value,
            "quantity": m.quantity,
            "quantity_before": m.quantity_before,
            "quantity_after": m.quantity_after,
            "unit_cost": m.unit_cost,
            "reason": m.reason,
            "reference_type": m.reference_type,
            "reference_id": str(m.reference_id) if m.reference_id else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in movements
    ]


@router.get("/product/{product_id}")
async def get_product_inventory(
    product_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory details for a specific product."""
    inventory = await inventory_service.get_or_create_inventory(db, str(product_id))
    
    return {
        "product_id": str(inventory.product_id),
        "quantity_on_hand": inventory.quantity_on_hand,
        "quantity_reserved": inventory.quantity_reserved,
        "quantity_available": inventory.quantity_available,
        "reorder_point": inventory.reorder_point,
        "reorder_quantity": inventory.reorder_quantity,
        "safety_stock": inventory.safety_stock,
        "cost_price": inventory.cost_price,
        "needs_reorder": inventory.needs_reorder,
        "last_restocked_at": inventory.last_restocked_at.isoformat() if inventory.last_restocked_at else None,
    }


@router.put("/product/{product_id}/settings")
async def update_inventory_settings(
    product_id: UUID,
    data: InventorySettingsUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update inventory settings for a product."""
    inventory = await inventory_service.get_or_create_inventory(db, str(product_id))
    
    if data.reorder_point is not None:
        inventory.reorder_point = data.reorder_point
    if data.reorder_quantity is not None:
        inventory.reorder_quantity = data.reorder_quantity
    if data.safety_stock is not None:
        inventory.safety_stock = data.safety_stock
    if data.max_stock is not None:
        inventory.max_stock = data.max_stock
    
    inventory.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Alerts
# ═══════════════════════════════════════════════════════════════════

@router.get("/alerts")
def get_inventory_alerts(
    resolved: bool = False,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get inventory alerts."""
    query = db.query(InventoryAlert).filter(
        InventoryAlert.business_id == current_user["business_id"],
        InventoryAlert.is_resolved == resolved,
    )
    
    alerts = query.order_by(InventoryAlert.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": str(a.id),
            "product_id": str(a.product_id),
            "alert_type": a.alert_type.value,
            "message": a.message,
            "current_quantity": a.current_quantity,
            "threshold_quantity": a.threshold_quantity,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an alert as resolved."""
    alert = db.query(InventoryAlert).filter(
        InventoryAlert.id == alert_id,
        InventoryAlert.business_id == current_user["business_id"],
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = current_user["user_id"]
    db.commit()
    
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# Suppliers
# ═══════════════════════════════════════════════════════════════════

@router.get("/suppliers")
def list_suppliers(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all suppliers."""
    query = db.query(Supplier).filter(
        Supplier.business_id == current_user["business_id"]
    )
    
    if active_only:
        query = query.filter(Supplier.is_active == True)
    
    suppliers = query.order_by(Supplier.name).all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "contact_name": s.contact_name,
            "email": s.email,
            "phone": s.phone,
            "payment_terms": s.payment_terms,
            "lead_time_days": s.lead_time_days,
            "rating": s.rating,
            "is_active": s.is_active,
        }
        for s in suppliers
    ]


@router.post("/suppliers")
def create_supplier(
    data: SupplierCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new supplier."""
    supplier = Supplier(
        business_id=current_user["business_id"],
        name=data.name,
        contact_name=data.contact_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        payment_terms=data.payment_terms,
        lead_time_days=data.lead_time_days,
    )
    db.add(supplier)
    db.commit()
    
    return {"success": True, "supplier_id": str(supplier.id)}


# ═══════════════════════════════════════════════════════════════════
# Purchase Orders
# ═══════════════════════════════════════════════════════════════════

@router.get("/purchase-orders")
def list_purchase_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List purchase orders."""
    query = db.query(PurchaseOrder).filter(
        PurchaseOrder.business_id == current_user["business_id"]
    )
    
    if status:
        try:
            query = query.filter(PurchaseOrder.status == PurchaseOrderStatus(status))
        except ValueError:
            pass
    
    pos = query.order_by(PurchaseOrder.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": str(po.id),
            "po_number": po.po_number,
            "supplier_id": str(po.supplier_id),
            "supplier_name": po.supplier.name if po.supplier else None,
            "status": po.status.value,
            "total": po.total,
            "expected_date": po.expected_date.isoformat() if po.expected_date else None,
            "created_at": po.created_at.isoformat(),
        }
        for po in pos
    ]


@router.post("/purchase-orders")
async def create_purchase_order(
    data: PurchaseOrderCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new purchase order."""
    items = [
        {
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_cost": item.unit_cost,
            "notes": item.notes,
        }
        for item in data.items
    ]
    
    result = await inventory_service.create_purchase_order(
        db=db,
        business_id=str(current_user["business_id"]),
        supplier_id=data.supplier_id,
        items=items,
        notes=data.notes,
        expected_date=data.expected_date,
        created_by=str(current_user["user_id"]),
    )
    
    return result


@router.get("/purchase-orders/{po_id}")
def get_purchase_order(
    po_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get purchase order details."""
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == po_id,
        PurchaseOrder.business_id == current_user["business_id"],
    ).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "supplier": {
            "id": str(po.supplier.id),
            "name": po.supplier.name,
        } if po.supplier else None,
        "status": po.status.value,
        "subtotal": po.subtotal,
        "tax": po.tax,
        "total": po.total,
        "notes": po.notes,
        "expected_date": po.expected_date.isoformat() if po.expected_date else None,
        "received_date": po.received_date.isoformat() if po.received_date else None,
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "quantity_ordered": item.quantity_ordered,
                "quantity_received": item.quantity_received,
                "unit_cost": item.unit_cost,
                "total_cost": item.total_cost,
            }
            for item in po.items
        ],
        "created_at": po.created_at.isoformat(),
    }


@router.post("/purchase-orders/{po_id}/send")
def send_purchase_order(
    po_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark purchase order as sent to supplier."""
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == po_id,
        PurchaseOrder.business_id == current_user["business_id"],
    ).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    if po.status != PurchaseOrderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only send draft orders")
    
    po.status = PurchaseOrderStatus.ORDERED
    po.order_date = datetime.utcnow()
    db.commit()
    
    return {"success": True, "status": po.status.value}


@router.post("/purchase-orders/{po_id}/receive")
async def receive_purchase_order(
    po_id: UUID,
    data: ReceivePurchaseOrder,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Receive items from a purchase order."""
    items = [
        {"item_id": item.item_id, "quantity_received": item.quantity_received}
        for item in data.items
    ]
    
    result = await inventory_service.receive_purchase_order(
        db=db,
        business_id=str(current_user["business_id"]),
        po_id=str(po_id),
        items_received=items,
        created_by=str(current_user["user_id"]),
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
