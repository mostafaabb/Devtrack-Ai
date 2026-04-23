"""
Reports API - Export and report generation endpoints for DevTrack AI
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.db.session import get_db
from sqlalchemy.orm import Session
from app.services.report_service import report_service


router = APIRouter(prefix="/reports", tags=["reports"])


# =========================================================================
# SALES REPORTS
# =========================================================================

@router.get("/sales")
async def generate_sales_report(
    business_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    db: Session = Depends(get_db)
):
    """Generate a sales report for the specified period"""
    # Default to last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    buffer = await report_service.generate_sales_report(
        db=db,
        business_id=str(business_id),
        start_date=start_date,
        end_date=end_date,
        format=format
    )
    
    if format == "excel":
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=sales_report_{start_date.strftime('%Y%m%d')}.xlsx"}
        )
    else:
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=sales_report_{start_date.strftime('%Y%m%d')}.pdf"}
        )


@router.get("/inventory")
async def generate_inventory_report(
    business_id: UUID,
    include_movements: bool = Query(True),
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    db: Session = Depends(get_db)
):
    """Generate an inventory status report"""
    buffer = await report_service.generate_inventory_report(
        db=db,
        business_id=str(business_id),
        include_movements=include_movements,
        format=format
    )
    
    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d')}"
    
    if format == "excel":
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    else:
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )


@router.get("/customers")
async def generate_customer_report(
    business_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    db: Session = Depends(get_db)
):
    """Generate a customer analytics report"""
    buffer = await report_service.generate_customer_report(
        db=db,
        business_id=str(business_id),
        start_date=start_date,
        end_date=end_date,
        format=format
    )
    
    filename = f"customer_report_{datetime.now().strftime('%Y%m%d')}"
    
    if format == "excel":
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    else:
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )


@router.get("/financial")
async def generate_financial_report(
    business_id: UUID,
    year: int = Query(...),
    month: Optional[int] = Query(None, ge=1, le=12),
    format: str = Query("pdf", regex="^(pdf|excel)$"),
    db: Session = Depends(get_db)
):
    """Generate a financial summary report"""
    buffer = await report_service.generate_financial_summary(
        db=db,
        business_id=str(business_id),
        year=year,
        month=month,
        format=format
    )
    
    period = f"{year}" if not month else f"{year}_{month:02d}"
    filename = f"financial_report_{period}"
    
    if format == "excel":
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    else:
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )


# =========================================================================
# DATA EXPORTS
# =========================================================================

@router.get("/export/orders")
async def export_orders(
    business_id: UUID,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Export orders to Excel"""
    buffer = await report_service.export_orders(
        db=db,
        business_id=str(business_id),
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    
    filename = f"orders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/customers")
async def export_customers(
    business_id: UUID,
    include_stats: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Export customers to Excel"""
    buffer = await report_service.export_customers(
        db=db,
        business_id=str(business_id),
        include_stats=include_stats
    )
    
    filename = f"customers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/products")
async def export_products(
    business_id: UUID,
    include_inventory: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Export products to Excel"""
    buffer = await report_service.export_products(
        db=db,
        business_id=str(business_id),
        include_inventory=include_inventory
    )
    
    filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
