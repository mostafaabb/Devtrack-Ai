"""
Inventory Service - Stock management and tracking.
Handles stock movements, alerts, reorder points, and purchase orders.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID
import random
import string

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.inventory import (
    ProductInventory, StockMovement, StockMovementType,
    PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus,
    InventoryAlert, AlertType, Supplier
)
from app.models.product import Product

logger = logging.getLogger("devtrack.inventory")


class InventoryService:
    """
    Inventory management service.
    Tracks stock levels, movements, and generates alerts.
    """

    def _generate_po_number(self) -> str:
        """Generate unique purchase order number."""
        chars = string.ascii_uppercase + string.digits
        return f"PO-{''.join(random.choices(chars, k=8))}"

    async def get_or_create_inventory(
        self,
        db: Session,
        product_id: str,
        location_id: str = None,
    ) -> ProductInventory:
        """Get or create inventory record for a product."""
        inventory = db.query(ProductInventory).filter(
            ProductInventory.product_id == product_id
        ).first()

        if not inventory:
            inventory = ProductInventory(
                product_id=product_id,
                location_id=location_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                quantity_available=0,
            )
            db.add(inventory)
            db.flush()

        return inventory

    async def adjust_stock(
        self,
        db: Session,
        business_id: str,
        product_id: str,
        quantity: int,
        movement_type: StockMovementType,
        reason: str = None,
        reference_type: str = None,
        reference_id: str = None,
        unit_cost: float = None,
        created_by: str = None,
        location_id: str = None,
    ) -> Dict[str, Any]:
        """
        Adjust stock for a product.
        Positive quantity = stock in, Negative = stock out.
        """
        inventory = await self.get_or_create_inventory(db, product_id, location_id)
        
        quantity_before = inventory.quantity_on_hand
        quantity_after = quantity_before + quantity

        if quantity_after < 0:
            return {
                "success": False,
                "error": "Insufficient stock",
                "available": inventory.quantity_available,
            }

        # Create stock movement record
        movement = StockMovement(
            business_id=business_id,
            product_id=product_id,
            location_id=location_id,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            unit_cost=unit_cost,
            total_cost=abs(quantity) * unit_cost if unit_cost else None,
            reference_type=reference_type,
            reference_id=reference_id,
            reason=reason,
            created_by=created_by,
        )
        db.add(movement)

        # Update inventory
        inventory.quantity_on_hand = quantity_after
        inventory.quantity_available = quantity_after - inventory.quantity_reserved
        inventory.updated_at = datetime.utcnow()

        if movement_type == StockMovementType.PURCHASE:
            inventory.last_restocked_at = datetime.utcnow()
            if unit_cost:
                inventory.last_cost_price = unit_cost
                # Update average cost
                if inventory.cost_price == 0:
                    inventory.cost_price = unit_cost
                else:
                    inventory.cost_price = (inventory.cost_price + unit_cost) / 2

        db.commit()

        # Check for low stock alerts
        await self._check_stock_alerts(db, business_id, product_id, inventory)

        return {
            "success": True,
            "movement_id": str(movement.id),
            "quantity_before": quantity_before,
            "quantity_after": quantity_after,
            "quantity_available": inventory.quantity_available,
        }

    async def reserve_stock(
        self,
        db: Session,
        product_id: str,
        quantity: int,
    ) -> Dict[str, Any]:
        """Reserve stock for an order (doesn't reduce on_hand yet)."""
        inventory = await self.get_or_create_inventory(db, product_id)

        if inventory.quantity_available < quantity:
            return {
                "success": False,
                "error": "Insufficient stock",
                "available": inventory.quantity_available,
            }

        inventory.quantity_reserved += quantity
        inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
        db.commit()

        return {
            "success": True,
            "reserved": quantity,
            "available": inventory.quantity_available,
        }

    async def release_reservation(
        self,
        db: Session,
        product_id: str,
        quantity: int,
    ) -> Dict[str, Any]:
        """Release reserved stock (order cancelled)."""
        inventory = await self.get_or_create_inventory(db, product_id)

        inventory.quantity_reserved = max(0, inventory.quantity_reserved - quantity)
        inventory.quantity_available = inventory.quantity_on_hand - inventory.quantity_reserved
        db.commit()

        return {
            "success": True,
            "released": quantity,
            "available": inventory.quantity_available,
        }

    async def fulfill_order(
        self,
        db: Session,
        business_id: str,
        order_id: str,
        items: List[Dict[str, Any]],
        created_by: str = None,
    ) -> Dict[str, Any]:
        """
        Fulfill an order by reducing stock.
        Items: [{"product_id": "...", "quantity": 1}, ...]
        """
        results = []
        
        for item in items:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 1)
            
            if not product_id:
                continue

            # Reduce reserved and on_hand
            inventory = await self.get_or_create_inventory(db, product_id)
            inventory.quantity_reserved = max(0, inventory.quantity_reserved - quantity)

            result = await self.adjust_stock(
                db=db,
                business_id=business_id,
                product_id=product_id,
                quantity=-quantity,
                movement_type=StockMovementType.SALE,
                reference_type="order",
                reference_id=order_id,
                reason=f"Order fulfillment",
                created_by=created_by,
            )
            results.append(result)

        return {
            "success": all(r.get("success") for r in results),
            "items": results,
        }

    async def _check_stock_alerts(
        self,
        db: Session,
        business_id: str,
        product_id: str,
        inventory: ProductInventory,
    ):
        """Check and create stock alerts if needed."""
        # Check for out of stock
        if inventory.quantity_available <= 0:
            existing = db.query(InventoryAlert).filter(
                InventoryAlert.product_id == product_id,
                InventoryAlert.alert_type == AlertType.OUT_OF_STOCK,
                InventoryAlert.is_resolved == False,
            ).first()

            if not existing:
                alert = InventoryAlert(
                    business_id=business_id,
                    product_id=product_id,
                    alert_type=AlertType.OUT_OF_STOCK,
                    message=f"Product is out of stock",
                    current_quantity=inventory.quantity_available,
                    threshold_quantity=0,
                )
                db.add(alert)

        # Check for low stock
        elif inventory.quantity_available <= inventory.reorder_point:
            existing = db.query(InventoryAlert).filter(
                InventoryAlert.product_id == product_id,
                InventoryAlert.alert_type == AlertType.LOW_STOCK,
                InventoryAlert.is_resolved == False,
            ).first()

            if not existing:
                alert = InventoryAlert(
                    business_id=business_id,
                    product_id=product_id,
                    alert_type=AlertType.LOW_STOCK,
                    message=f"Stock below reorder point ({inventory.reorder_point})",
                    current_quantity=inventory.quantity_available,
                    threshold_quantity=inventory.reorder_point,
                )
                db.add(alert)

        # Resolve alerts if stock is OK
        else:
            db.query(InventoryAlert).filter(
                InventoryAlert.product_id == product_id,
                InventoryAlert.alert_type.in_([AlertType.LOW_STOCK, AlertType.OUT_OF_STOCK]),
                InventoryAlert.is_resolved == False,
            ).update({
                "is_resolved": True,
                "resolved_at": datetime.utcnow(),
            })

        db.commit()

    async def create_purchase_order(
        self,
        db: Session,
        business_id: str,
        supplier_id: str,
        items: List[Dict[str, Any]],
        notes: str = None,
        expected_date: datetime = None,
        created_by: str = None,
        location_id: str = None,
    ) -> Dict[str, Any]:
        """
        Create a purchase order for restocking.
        Items: [{"product_id": "...", "quantity": 10, "unit_cost": 5.00}, ...]
        """
        # Calculate totals
        subtotal = sum(item.get("quantity", 0) * item.get("unit_cost", 0) for item in items)
        tax = subtotal * 0.11  # 11% VAT
        total = subtotal + tax

        po = PurchaseOrder(
            business_id=business_id,
            supplier_id=supplier_id,
            location_id=location_id,
            po_number=self._generate_po_number(),
            status=PurchaseOrderStatus.DRAFT,
            subtotal=round(subtotal, 2),
            tax=round(tax, 2),
            total=round(total, 2),
            notes=notes,
            expected_date=expected_date,
            created_by=created_by,
        )
        db.add(po)
        db.flush()

        # Add items
        for item_data in items:
            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=item_data.get("product_id"),
                quantity_ordered=item_data.get("quantity", 1),
                unit_cost=item_data.get("unit_cost", 0),
                total_cost=item_data.get("quantity", 1) * item_data.get("unit_cost", 0),
                notes=item_data.get("notes"),
            )
            db.add(item)

        db.commit()

        return {
            "success": True,
            "purchase_order_id": str(po.id),
            "po_number": po.po_number,
            "total": po.total,
        }

    async def receive_purchase_order(
        self,
        db: Session,
        business_id: str,
        po_id: str,
        items_received: List[Dict[str, Any]],
        created_by: str = None,
    ) -> Dict[str, Any]:
        """
        Receive items from a purchase order.
        Items: [{"item_id": "...", "quantity_received": 10}, ...]
        """
        po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
        if not po:
            return {"success": False, "error": "Purchase order not found"}

        all_received = True
        
        for received in items_received:
            item = db.query(PurchaseOrderItem).filter(
                PurchaseOrderItem.id == received.get("item_id")
            ).first()
            
            if not item:
                continue

            qty = received.get("quantity_received", 0)
            item.quantity_received += qty

            if item.quantity_received < item.quantity_ordered:
                all_received = False

            # Add stock
            await self.adjust_stock(
                db=db,
                business_id=business_id,
                product_id=str(item.product_id),
                quantity=qty,
                movement_type=StockMovementType.PURCHASE,
                reference_type="purchase_order",
                reference_id=str(po.id),
                unit_cost=item.unit_cost,
                reason=f"PO #{po.po_number} received",
                created_by=created_by,
            )

        # Update PO status
        if all_received:
            po.status = PurchaseOrderStatus.RECEIVED
            po.received_date = datetime.utcnow()
        else:
            po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

        db.commit()

        return {
            "success": True,
            "status": po.status.value,
            "fully_received": all_received,
        }

    def get_inventory_summary(self, db: Session, business_id: str) -> Dict[str, Any]:
        """Get inventory summary for a business."""
        products = db.query(Product).filter(
            Product.business_id == business_id,
            Product.track_inventory == True,
        ).all()

        product_ids = [str(p.id) for p in products]
        
        inventories = db.query(ProductInventory).filter(
            ProductInventory.product_id.in_(product_ids)
        ).all()

        alerts = db.query(InventoryAlert).filter(
            InventoryAlert.business_id == business_id,
            InventoryAlert.is_resolved == False,
        ).all()

        total_value = sum(
            inv.quantity_on_hand * inv.cost_price 
            for inv in inventories
        )

        low_stock = [inv for inv in inventories if inv.needs_reorder]
        out_of_stock = [inv for inv in inventories if inv.quantity_available <= 0]

        return {
            "total_products": len(products),
            "tracked_products": len(inventories),
            "total_inventory_value": round(total_value, 2),
            "low_stock_count": len(low_stock),
            "out_of_stock_count": len(out_of_stock),
            "active_alerts": len(alerts),
        }

    def get_stock_movements(
        self,
        db: Session,
        business_id: str,
        product_id: str = None,
        movement_type: StockMovementType = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[StockMovement]:
        """Get stock movement history."""
        query = db.query(StockMovement).filter(
            StockMovement.business_id == business_id
        )

        if product_id:
            query = query.filter(StockMovement.product_id == product_id)
        
        if movement_type:
            query = query.filter(StockMovement.movement_type == movement_type)

        return query.order_by(
            StockMovement.created_at.desc()
        ).offset(offset).limit(limit).all()


# Global instance
inventory_service = InventoryService()
