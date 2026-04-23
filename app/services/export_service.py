"""
Data Export Service — Generates CSV exports for business data.
Supports customers, orders, bookings, products, and conversations.
"""
import csv
import io
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.booking import Booking
from app.models.product import Product
from app.models.conversation import Conversation, Message


class ExportService:
    """Export business data in various formats."""

    def export_customers(self, db: Session, business_id: str,
                          date_from: Optional[datetime] = None,
                          date_to: Optional[datetime] = None) -> str:
        """Export customers as CSV."""
        query = db.query(Customer).filter(Customer.business_id == business_id)
        if date_from:
            query = query.filter(Customer.created_at >= date_from)
        if date_to:
            query = query.filter(Customer.created_at <= date_to)

        customers = query.order_by(Customer.created_at.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "Email", "Phone", "Channel", "Total Orders",
                          "Total Spent", "Created At"])

        for c in customers:
            order_count = db.query(func.count(Order.id)).filter(
                Order.customer_id == c.id
            ).scalar() or 0
            total_spent = db.query(func.sum(Order.total)).filter(
                Order.customer_id == c.id, Order.status == "completed"
            ).scalar() or 0.0

            writer.writerow([
                c.name, c.email or "", c.phone or "", c.channel or "web",
                order_count, f"${total_spent:.2f}", c.created_at.strftime("%Y-%m-%d %H:%M")
            ])

        return output.getvalue()

    def export_orders(self, db: Session, business_id: str,
                       date_from: Optional[datetime] = None,
                       date_to: Optional[datetime] = None) -> str:
        """Export orders as CSV."""
        query = db.query(Order).filter(Order.business_id == business_id)
        if date_from:
            query = query.filter(Order.created_at >= date_from)
        if date_to:
            query = query.filter(Order.created_at <= date_to)

        orders = query.order_by(Order.created_at.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Order Number", "Customer", "Status", "Type", "Subtotal",
                          "Tax", "Total", "Source", "Notes", "Created At", "Completed At"])

        for o in orders:
            customer = db.query(Customer).filter(Customer.id == o.customer_id).first()
            customer_name = customer.name if customer else "Walk-in"

            writer.writerow([
                o.order_number, customer_name, o.status.value if hasattr(o.status, 'value') else o.status,
                o.order_type or "dine_in", f"${o.subtotal:.2f}", f"${o.tax:.2f}",
                f"${o.total:.2f}", o.source or "manual", o.notes or "",
                o.created_at.strftime("%Y-%m-%d %H:%M"),
                o.completed_at.strftime("%Y-%m-%d %H:%M") if o.completed_at else ""
            ])

        return output.getvalue()

    def export_bookings(self, db: Session, business_id: str,
                         date_from: Optional[datetime] = None,
                         date_to: Optional[datetime] = None) -> str:
        """Export bookings as CSV."""
        query = db.query(Booking).filter(Booking.business_id == business_id)
        if date_from:
            query = query.filter(Booking.created_at >= date_from)
        if date_to:
            query = query.filter(Booking.created_at <= date_to)

        bookings = query.order_by(Booking.start_time.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Booking Number", "Customer", "Status", "Type", "Service",
                          "Start Time", "Duration (min)", "Party Size", "Source", "Notes"])

        for b in bookings:
            customer = db.query(Customer).filter(Customer.id == b.customer_id).first()
            customer_name = customer.name if customer else "Guest"

            writer.writerow([
                b.booking_number, customer_name,
                b.status.value if hasattr(b.status, 'value') else b.status,
                b.booking_type or "", b.service_name or "",
                b.start_time.strftime("%Y-%m-%d %H:%M") if b.start_time else "",
                b.duration_minutes or "", b.party_size or "",
                b.source or "manual", b.notes or ""
            ])

        return output.getvalue()

    def export_products(self, db: Session, business_id: str) -> str:
        """Export products as CSV."""
        products = db.query(Product).filter(
            Product.business_id == business_id
        ).order_by(Product.name).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Name", "SKU", "Price", "Sale Price", "Stock", "Category",
                          "Status", "Created At"])

        for p in products:
            writer.writerow([
                p.name, p.sku or "", f"${p.price:.2f}" if p.price else "",
                f"${p.sale_price:.2f}" if p.sale_price else "",
                p.stock_quantity if p.stock_quantity is not None else "N/A",
                "", "Active" if p.is_active else "Inactive",
                p.created_at.strftime("%Y-%m-%d %H:%M")
            ])

        return output.getvalue()

    def export_conversations(self, db: Session, business_id: str,
                              date_from: Optional[datetime] = None,
                              date_to: Optional[datetime] = None) -> str:
        """Export conversation summaries as CSV."""
        query = db.query(Conversation).filter(Conversation.business_id == business_id)
        if date_from:
            query = query.filter(Conversation.created_at >= date_from)
        if date_to:
            query = query.filter(Conversation.created_at <= date_to)

        conversations = query.order_by(Conversation.created_at.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Customer", "Status", "Channel", "Messages Count",
                          "Last Message", "Started At"])

        for conv in conversations:
            customer = db.query(Customer).filter(Customer.id == conv.customer_id).first()
            customer_name = customer.name if customer else "Unknown"
            msg_count = db.query(func.count(Message.id)).filter(
                Message.conversation_id == conv.id
            ).scalar() or 0

            writer.writerow([
                str(conv.id)[:8], customer_name,
                conv.status.value if hasattr(conv.status, 'value') else conv.status,
                conv.channel or "web", msg_count,
                conv.last_message_at.strftime("%Y-%m-%d %H:%M") if conv.last_message_at else "",
                conv.created_at.strftime("%Y-%m-%d %H:%M")
            ])

        return output.getvalue()


# Global instance
export_service = ExportService()
