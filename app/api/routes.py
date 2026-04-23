"""
Customers, Orders, Bookings, Products, Services, Documents, Workflows, and Analytics API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import os
import uuid as uuid_mod
import random
import string

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.booking import Booking, BookingStatus
from app.models.product import Product, Category
from app.models.service import Service
from app.models.document import Document, DocumentChunk
from app.models.workflow import Workflow, WorkflowStatus
from app.models.analytics import AnalyticsEvent
from app.models.conversation import Conversation, Message, ConversationStatus
from app.schemas.schemas import (
    CustomerCreate, CustomerResponse,
    OrderCreate, OrderUpdate, OrderResponse,
    BookingCreate, BookingUpdate, BookingResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    CategoryCreate, CategoryResponse,
    ServiceCreate, ServiceResponse,
    DocumentResponse,
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    AnalyticsSummary,
)
from app.services.rag_service import rag_service
from app.services.ai_service import ai_service


# ═══════════════════════════════════════════════════════════════════
# CUSTOMERS
# ═══════════════════════════════════════════════════════════════════

customers_router = APIRouter(prefix="/customers", tags=["Customers"])


@customers_router.get("/", response_model=List[CustomerResponse])
def list_customers(
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all customers for the business."""
    query = db.query(Customer).filter(
        Customer.business_id == current_user["business_id"]
    )
    if search:
        query = query.filter(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.email.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )
    return query.order_by(Customer.created_at.desc()).offset(offset).limit(limit).all()


@customers_router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific customer's profile."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.business_id == current_user["business_id"]
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@customers_router.post("/", response_model=CustomerResponse)
def create_customer(
    data: CustomerCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new customer."""
    customer = Customer(
        business_id=current_user["business_id"],
        name=data.name,
        email=data.email,
        phone=data.phone,
        channel=data.channel,
        tags=data.tags or [],
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


# ═══════════════════════════════════════════════════════════════════
# ORDERS
# ═══════════════════════════════════════════════════════════════════

orders_router = APIRouter(prefix="/orders", tags=["Orders"])


def _generate_order_number() -> str:
    """Generate a unique order number."""
    chars = string.ascii_uppercase + string.digits
    return f"ORD-{''.join(random.choices(chars, k=8))}"


@orders_router.get("/", response_model=List[OrderResponse])
def list_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all orders for the business."""
    query = db.query(Order).filter(
        Order.business_id == current_user["business_id"]
    )
    if status:
        query = query.filter(Order.status == status)
    return query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()


@orders_router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific order."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user["business_id"]
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@orders_router.post("/", response_model=OrderResponse)
def create_order(
    data: OrderCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new order."""
    # Calculate totals
    subtotal = sum(item.quantity * item.unit_price for item in data.items)
    tax = subtotal * 0.11  # 11% VAT (Lebanon)
    total = subtotal + tax
    
    order = Order(
        business_id=current_user["business_id"],
        customer_id=data.customer_id,
        order_number=_generate_order_number(),
        order_type=data.order_type,
        subtotal=round(subtotal, 2),
        tax=round(tax, 2),
        total=round(total, 2),
        delivery_address=data.delivery_address,
        delivery_notes=data.delivery_notes,
        notes=data.notes,
        source=data.source,
    )
    db.add(order)
    db.flush()
    
    # Add order items
    for item_data in data.items:
        item = OrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            name=item_data.name,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=round(item_data.quantity * item_data.unit_price, 2),
            notes=item_data.notes,
        )
        db.add(item)
    
    # Track analytics
    event = AnalyticsEvent(
        business_id=current_user["business_id"],
        event_type="order",
        event_action="created",
        entity_type="order",
        entity_id=str(order.id),
        value=total,
    )
    db.add(event)
    
    db.commit()
    db.refresh(order)
    return order


@orders_router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: UUID,
    data: OrderUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status or notes."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user["business_id"]
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if data.status:
        order.status = data.status
        if data.status == "completed":
            order.completed_at = datetime.utcnow()
    if data.notes is not None:
        order.notes = data.notes
    
    db.commit()
    db.refresh(order)
    return order


# ═══════════════════════════════════════════════════════════════════
# BOOKINGS
# ═══════════════════════════════════════════════════════════════════

bookings_router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _generate_booking_number() -> str:
    """Generate a unique booking number."""
    chars = string.ascii_uppercase + string.digits
    return f"BKG-{''.join(random.choices(chars, k=8))}"


@bookings_router.get("/", response_model=List[BookingResponse])
def list_bookings(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all bookings for the business."""
    query = db.query(Booking).filter(
        Booking.business_id == current_user["business_id"]
    )
    if status:
        query = query.filter(Booking.status == status)
    return query.order_by(Booking.start_time.desc()).offset(offset).limit(limit).all()


@bookings_router.post("/", response_model=BookingResponse)
def create_booking(
    data: BookingCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new booking."""
    booking = Booking(
        business_id=current_user["business_id"],
        customer_id=data.customer_id,
        booking_number=_generate_booking_number(),
        booking_type=data.booking_type,
        start_time=data.start_time,
        end_time=data.end_time,
        duration_minutes=data.duration_minutes,
        party_size=data.party_size,
        resource_name=data.resource_name,
        service_name=data.service_name,
        notes=data.notes,
        source=data.source,
    )
    db.add(booking)
    
    # Track analytics
    event = AnalyticsEvent(
        business_id=current_user["business_id"],
        event_type="booking",
        event_action="created",
        entity_type="booking",
        entity_id=str(booking.id),
    )
    db.add(event)
    
    db.commit()
    db.refresh(booking)
    return booking


@bookings_router.put("/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: UUID,
    data: BookingUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update booking status or details."""
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.business_id == current_user["business_id"]
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(booking, key, value)
    
    db.commit()
    db.refresh(booking)
    return booking


# ═══════════════════════════════════════════════════════════════════
# PRODUCTS
# ═══════════════════════════════════════════════════════════════════

products_router = APIRouter(prefix="/products", tags=["Products"])


@products_router.get("/", response_model=List[ProductResponse])
def list_products(
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all products for the business."""
    query = db.query(Product).filter(
        Product.business_id == current_user["business_id"]
    )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    return query.order_by(Product.sort_order).all()


@products_router.post("/", response_model=ProductResponse)
def create_product(
    data: ProductCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new product."""
    product = Product(
        business_id=current_user["business_id"],
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        price=data.price,
        sale_price=data.sale_price,
        sku=data.sku,
        stock_quantity=data.stock_quantity,
        track_inventory=data.track_inventory,
        image_url=data.image_url,
        attributes=data.attributes or {},
        tags=data.tags or [],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@products_router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    data: ProductUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a product."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == current_user["business_id"]
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    
    db.commit()
    db.refresh(product)
    return product


@products_router.delete("/{product_id}")
def delete_product(
    product_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a product."""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == current_user["business_id"]
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}


# ─── Categories ─────────────────────────────────────────────────

categories_router = APIRouter(prefix="/categories", tags=["Categories"])


@categories_router.get("/", response_model=List[CategoryResponse])
def list_categories(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all categories for the business."""
    return db.query(Category).filter(
        Category.business_id == current_user["business_id"]
    ).order_by(Category.sort_order).all()


@categories_router.post("/", response_model=CategoryResponse)
def create_category(
    data: CategoryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new category."""
    category = Category(
        business_id=current_user["business_id"],
        name=data.name,
        description=data.description,
        icon=data.icon,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# ═══════════════════════════════════════════════════════════════════
# SERVICES
# ═══════════════════════════════════════════════════════════════════

services_router = APIRouter(prefix="/services", tags=["Services"])


@services_router.get("/", response_model=List[ServiceResponse])
def list_services(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all services for the business."""
    return db.query(Service).filter(
        Service.business_id == current_user["business_id"]
    ).order_by(Service.sort_order).all()


@services_router.post("/", response_model=ServiceResponse)
def create_service(
    data: ServiceCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new service."""
    service = Service(
        business_id=current_user["business_id"],
        name=data.name,
        description=data.description,
        duration_minutes=data.duration_minutes,
        price=data.price,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


# ═══════════════════════════════════════════════════════════════════
# DOCUMENTS (Knowledge Base)
# ═══════════════════════════════════════════════════════════════════

documents_router = APIRouter(prefix="/documents", tags=["Documents"])


@documents_router.get("/", response_model=List[DocumentResponse])
def list_documents(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all uploaded documents."""
    return db.query(Document).filter(
        Document.business_id == current_user["business_id"]
    ).order_by(Document.created_at.desc()).all()


@documents_router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document for the knowledge base.
    Supports PDF, TXT, DOCX files.
    """
    # Validate file type
    allowed_types = {"pdf", "txt", "docx"}
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type not supported. Allowed: {allowed_types}")
    
    # Save file
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid_mod.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.{file_ext}")
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document record
    document = Document(
        business_id=current_user["business_id"],
        title=title,
        filename=file.filename,
        file_type=file_ext,
        file_size=len(content),
        file_path=file_path,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process document (extract text, chunk, embed)
    try:
        text = rag_service.extract_text(file_path, file_ext)
        if text:
            document.raw_text = text
            chunks = rag_service.chunk_text(text)
            chunk_count = rag_service.add_chunks(chunks, str(document.id))
            
            # Save chunks to database
            for i, chunk in enumerate(chunks):
                db_chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk,
                    chunk_index=i,
                    token_count=len(chunk.split()),
                )
                db.add(db_chunk)
            
            document.chunk_count = chunk_count
            document.status = "processed"
            document.processed_at = datetime.utcnow()
        else:
            document.status = "failed"
    except Exception as e:
        document.status = "failed"
    
    db.commit()
    db.refresh(document)
    return document


@documents_router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document from the knowledge base."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.business_id == current_user["business_id"]
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    db.delete(document)
    db.commit()
    return {"message": "Document deleted"}


# ═══════════════════════════════════════════════════════════════════
# WORKFLOWS (Automation)
# ═══════════════════════════════════════════════════════════════════

workflows_router = APIRouter(prefix="/workflows", tags=["Workflows"])


@workflows_router.get("/", response_model=List[WorkflowResponse])
def list_workflows(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all workflows for the business."""
    return db.query(Workflow).filter(
        Workflow.business_id == current_user["business_id"]
    ).order_by(Workflow.created_at.desc()).all()


@workflows_router.post("/", response_model=WorkflowResponse)
def create_workflow(
    data: WorkflowCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workflow automation rule."""
    workflow = Workflow(
        business_id=current_user["business_id"],
        name=data.name,
        description=data.description,
        trigger_type=data.trigger_type,
        trigger_conditions=data.trigger_conditions or {},
        action_type=data.action_type,
        action_config=data.action_config or {},
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@workflows_router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a workflow."""
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.business_id == current_user["business_id"]
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and value:
            workflow.status = WorkflowStatus(value)
        elif value is not None:
            setattr(workflow, key, value)
    
    db.commit()
    db.refresh(workflow)
    return workflow


@workflows_router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.business_id == current_user["business_id"]
    ).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db.delete(workflow)
    db.commit()
    return {"message": "Workflow deleted"}


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics summary for the dashboard."""
    business_id = current_user["business_id"]
    
    total_customers = db.query(func.count(Customer.id)).filter(
        Customer.business_id == business_id
    ).scalar() or 0
    
    total_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.business_id == business_id
    ).scalar() or 0
    
    total_orders = db.query(func.count(Order.id)).filter(
        Order.business_id == business_id
    ).scalar() or 0
    
    total_bookings = db.query(func.count(Booking.id)).filter(
        Booking.business_id == business_id
    ).scalar() or 0
    
    total_revenue = db.query(func.sum(Order.total)).filter(
        Order.business_id == business_id,
        Order.status == OrderStatus.COMPLETED
    ).scalar() or 0.0
    
    active_conversations = db.query(func.count(Conversation.id)).filter(
        Conversation.business_id == business_id,
        Conversation.status.in_([ConversationStatus.ACTIVE, ConversationStatus.AI_HANDLING])
    ).scalar() or 0
    
    pending_orders = db.query(func.count(Order.id)).filter(
        Order.business_id == business_id,
        Order.status == OrderStatus.PENDING
    ).scalar() or 0
    
    pending_bookings = db.query(func.count(Booking.id)).filter(
        Booking.business_id == business_id,
        Booking.status == BookingStatus.PENDING
    ).scalar() or 0
    
    return AnalyticsSummary(
        total_customers=total_customers,
        total_conversations=total_conversations,
        total_orders=total_orders,
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        active_conversations=active_conversations,
        pending_orders=pending_orders,
        pending_bookings=pending_bookings,
    )


@analytics_router.get("/insights")
async def get_ai_insights(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI-generated business insights."""
    business_id = current_user["business_id"]
    
    # Gather data for AI analysis
    data = {
        "total_customers": db.query(func.count(Customer.id)).filter(Customer.business_id == business_id).scalar() or 0,
        "total_orders": db.query(func.count(Order.id)).filter(Order.business_id == business_id).scalar() or 0,
        "total_revenue": float(db.query(func.sum(Order.total)).filter(Order.business_id == business_id, Order.status == OrderStatus.COMPLETED).scalar() or 0),
        "total_conversations": db.query(func.count(Conversation.id)).filter(Conversation.business_id == business_id).scalar() or 0,
        "total_bookings": db.query(func.count(Booking.id)).filter(Booking.business_id == business_id).scalar() or 0,
    }
    
    insights = await ai_service.generate_insights(data)
    
    return {"insights": insights, "data": data}


@analytics_router.get("/chart-data")
def get_chart_data(
    period: str = "week",  # week, month, year
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get REAL chart data from the database for the analytics dashboard."""
    from datetime import timedelta
    from sqlalchemy import cast, Date, extract

    business_id = current_user["business_id"]
    now = datetime.utcnow()

    if period == "week":
        # Last 7 days
        start_date = now - timedelta(days=6)
        labels = []
        orders_data = []
        revenue_data = []
        conversations_data = []
        customers_data = []
        
        for i in range(7):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            labels.append(day.strftime("%a"))  # Mon, Tue, etc.
            
            orders_count = db.query(func.count(Order.id)).filter(
                Order.business_id == business_id,
                Order.created_at >= day_start, Order.created_at < day_end
            ).scalar() or 0
            orders_data.append(orders_count)
            
            rev = db.query(func.sum(Order.total)).filter(
                Order.business_id == business_id,
                Order.created_at >= day_start, Order.created_at < day_end
            ).scalar() or 0
            revenue_data.append(float(rev))
            
            conv_count = db.query(func.count(Conversation.id)).filter(
                Conversation.business_id == business_id,
                Conversation.created_at >= day_start, Conversation.created_at < day_end
            ).scalar() or 0
            conversations_data.append(conv_count)
            
            cust_count = db.query(func.count(Customer.id)).filter(
                Customer.business_id == business_id,
                Customer.created_at >= day_start, Customer.created_at < day_end
            ).scalar() or 0
            customers_data.append(cust_count)

    elif period == "month":
        # Last 4 weeks
        labels = []
        orders_data = []
        revenue_data = []
        conversations_data = []
        customers_data = []
        
        for i in range(4):
            week_end = now - timedelta(weeks=3-i)
            week_start = week_end - timedelta(weeks=1)
            labels.append(f"Week {i+1}")
            
            orders_data.append(db.query(func.count(Order.id)).filter(
                Order.business_id == business_id,
                Order.created_at >= week_start, Order.created_at < week_end
            ).scalar() or 0)
            
            rev = db.query(func.sum(Order.total)).filter(
                Order.business_id == business_id,
                Order.created_at >= week_start, Order.created_at < week_end
            ).scalar() or 0
            revenue_data.append(float(rev))
            
            conversations_data.append(db.query(func.count(Conversation.id)).filter(
                Conversation.business_id == business_id,
                Conversation.created_at >= week_start, Conversation.created_at < week_end
            ).scalar() or 0)
            
            customers_data.append(db.query(func.count(Customer.id)).filter(
                Customer.business_id == business_id,
                Customer.created_at >= week_start, Customer.created_at < week_end
            ).scalar() or 0)
    else:
        # Last 12 months
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        orders_data = []
        revenue_data = []
        conversations_data = []
        customers_data = []
        current_year = now.year
        
        for month in range(1, 13):
            orders_data.append(db.query(func.count(Order.id)).filter(
                Order.business_id == business_id,
                extract('year', Order.created_at) == current_year,
                extract('month', Order.created_at) == month,
            ).scalar() or 0)
            
            rev = db.query(func.sum(Order.total)).filter(
                Order.business_id == business_id,
                extract('year', Order.created_at) == current_year,
                extract('month', Order.created_at) == month,
            ).scalar() or 0
            revenue_data.append(float(rev))
            
            conversations_data.append(db.query(func.count(Conversation.id)).filter(
                Conversation.business_id == business_id,
                extract('year', Conversation.created_at) == current_year,
                extract('month', Conversation.created_at) == month,
            ).scalar() or 0)
            
            customers_data.append(db.query(func.count(Customer.id)).filter(
                Customer.business_id == business_id,
                extract('year', Customer.created_at) == current_year,
                extract('month', Customer.created_at) == month,
            ).scalar() or 0)

    return {
        "labels": labels,
        "orders": orders_data,
        "revenue": revenue_data,
        "conversations": conversations_data,
        "customers": customers_data,
    }


# ═══════════════════════════════════════════════════════════════════
# DATA EXPORT
# ═══════════════════════════════════════════════════════════════════

from fastapi.responses import StreamingResponse

@analytics_router.get("/export/{entity_type}")
def export_data(
    entity_type: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export business data as CSV.
    Supported entity_types: customers, orders, bookings, products, conversations
    """
    from app.services.export_service import export_service
    import io

    # Parse dates
    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    export_map = {
        "customers": export_service.export_customers,
        "orders": export_service.export_orders,
        "bookings": export_service.export_bookings,
        "products": lambda db, bid, **kw: export_service.export_products(db, bid),
        "conversations": export_service.export_conversations,
    }

    if entity_type not in export_map:
        raise HTTPException(status_code=400, detail=f"Unsupported export type: {entity_type}")

    csv_data = export_map[entity_type](
        db=db, business_id=current_user["business_id"],
        date_from=dt_from, date_to=dt_to,
    ) if entity_type != "products" else export_service.export_products(db, current_user["business_id"])

    filename = f"{entity_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ═══════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════

from app.core.security import require_admin

@analytics_router.get("/audit-logs")
def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get audit logs for the business (admin only)."""
    from app.models.audit import AuditLog

    query = db.query(AuditLog).filter(
        AuditLog.business_id == current_user["business_id"]
    )
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": str(log.id),
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "description": log.description,
                "user_email": log.user_email,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": (offset // limit) + 1,
        "page_size": limit,
        "total_pages": (total + limit - 1) // limit,
    }
