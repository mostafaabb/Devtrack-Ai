"""
Report Generation Service - PDF and Excel exports for DevTrack AI
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating PDF and Excel reports"""
    
    def __init__(self):
        self.company_name = "DevTrack AI"
        self.primary_color = (41, 128, 185)  # Blue
        self.secondary_color = (52, 73, 94)  # Dark gray
    
    async def generate_sales_report(
        self,
        db,
        business_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "pdf"
    ) -> BytesIO:
        """
        Generate a sales report
        
        Args:
            db: Database session
            business_id: Business ID
            start_date: Report start date
            end_date: Report end date
            format: 'pdf' or 'excel'
            
        Returns:
            BytesIO buffer with the report
        """
        # Fetch data
        data = await self._fetch_sales_data(db, business_id, start_date, end_date)
        
        if format == "excel":
            return await self._generate_excel_report(data, "Sales Report", start_date, end_date)
        else:
            return await self._generate_pdf_sales_report(data, start_date, end_date)
    
    async def generate_inventory_report(
        self,
        db,
        business_id: str,
        include_movements: bool = True,
        format: str = "pdf"
    ) -> BytesIO:
        """Generate inventory status report"""
        data = await self._fetch_inventory_data(db, business_id, include_movements)
        
        if format == "excel":
            return await self._generate_excel_report(data, "Inventory Report")
        else:
            return await self._generate_pdf_inventory_report(data)
    
    async def generate_customer_report(
        self,
        db,
        business_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "pdf"
    ) -> BytesIO:
        """Generate customer analytics report"""
        data = await self._fetch_customer_data(db, business_id, start_date, end_date)
        
        if format == "excel":
            return await self._generate_excel_report(data, "Customer Report", start_date, end_date)
        else:
            return await self._generate_pdf_customer_report(data)
    
    async def generate_financial_summary(
        self,
        db,
        business_id: str,
        year: int,
        month: Optional[int] = None,
        format: str = "pdf"
    ) -> BytesIO:
        """Generate monthly or yearly financial summary"""
        data = await self._fetch_financial_data(db, business_id, year, month)
        
        if format == "excel":
            return await self._generate_excel_report(data, "Financial Summary")
        else:
            return await self._generate_pdf_financial_report(data, year, month)
    
    async def export_orders(
        self,
        db,
        business_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> BytesIO:
        """Export orders to Excel"""
        from app.models.order import Order
        from sqlalchemy import select, and_
        
        conditions = [Order.business_id == business_id]
        if start_date:
            conditions.append(Order.created_at >= start_date)
        if end_date:
            conditions.append(Order.created_at <= end_date)
        if status:
            conditions.append(Order.status == status)
        
        result = db.execute(
            select(Order).where(and_(*conditions)).order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        
        # Convert to export format
        rows = []
        for order in orders:
            rows.append({
                "Order Number": order.order_number,
                "Date": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "Customer": getattr(order, 'customer_name', 'N/A'),
                "Status": order.status,
                "Subtotal": order.subtotal or 0,
                "Tax": order.tax or 0,
                "Discount": order.discount or 0,
                "Total": order.total,
                "Payment Status": order.payment_status or 'pending',
                "Items Count": len(order.items) if hasattr(order, 'items') else 0
            })
        
        return await self._generate_excel_from_rows(rows, "Orders Export")
    
    async def export_customers(
        self,
        db,
        business_id: str,
        include_stats: bool = True
    ) -> BytesIO:
        """Export customers to Excel"""
        from app.models.customer import Customer
        from sqlalchemy import select
        
        result = db.execute(
            select(Customer).where(Customer.business_id == business_id)
        )
        customers = result.scalars().all()
        
        rows = []
        for customer in customers:
            row = {
                "Name": customer.name,
                "Email": customer.email or '',
                "Phone": customer.phone or '',
                "Created": customer.created_at.strftime("%Y-%m-%d"),
                "Tags": ', '.join(customer.tags) if customer.tags else '',
            }
            
            if include_stats:
                row["Total Orders"] = customer.total_orders or 0
                row["Total Spent"] = customer.total_spent or 0
                row["Last Order"] = customer.last_order_at.strftime("%Y-%m-%d") if customer.last_order_at else ''
            
            rows.append(row)
        
        return await self._generate_excel_from_rows(rows, "Customers Export")
    
    async def export_products(
        self,
        db,
        business_id: str,
        include_inventory: bool = True
    ) -> BytesIO:
        """Export products to Excel"""
        from app.models.product import Product
        from sqlalchemy import select
        
        result = db.execute(
            select(Product).where(Product.business_id == business_id)
        )
        products = result.scalars().all()
        
        rows = []
        for product in products:
            row = {
                "Name": product.name,
                "SKU": product.sku or '',
                "Category": product.category_id or '',
                "Price": product.price,
                "Status": 'Active' if product.is_active else 'Inactive',
            }
            
            if include_inventory:
                row["Stock"] = getattr(product, 'stock_quantity', 0) or 0
            
            rows.append(row)
        
        return await self._generate_excel_from_rows(rows, "Products Export")
    
    # =====================================================================
    # Private Helper Methods
    # =====================================================================
    
    async def _fetch_sales_data(
        self,
        db,
        business_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Fetch sales data for reporting"""
        from app.models.order import Order
        from sqlalchemy import select, func, and_
        
        # Total sales
        result = db.execute(
            select(
                func.count(Order.id).label('order_count'),
                func.sum(Order.total).label('total_revenue'),
                func.avg(Order.total).label('avg_order_value')
            ).where(
                and_(
                    Order.business_id == business_id,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status != 'cancelled'
                )
            )
        )
        totals = result.first()
        
        # Daily breakdown
        daily_result = db.execute(
            select(
                func.date(Order.created_at).label('date'),
                func.count(Order.id).label('orders'),
                func.sum(Order.total).label('revenue')
            ).where(
                and_(
                    Order.business_id == business_id,
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status != 'cancelled'
                )
            ).group_by(func.date(Order.created_at))
        )
        daily_data = [
            {
                "date": str(row.date),
                "orders": row.orders,
                "revenue": float(row.revenue or 0)
            }
            for row in daily_result.all()
        ]
        
        return {
            "summary": {
                "total_orders": totals.order_count or 0,
                "total_revenue": float(totals.total_revenue or 0),
                "avg_order_value": float(totals.avg_order_value or 0)
            },
            "daily": daily_data,
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            }
        }
    
    async def _fetch_inventory_data(
        self,
        db,
        business_id: str,
        include_movements: bool
    ) -> Dict[str, Any]:
        """Fetch inventory data for reporting"""
        from app.models.product import Product
        from sqlalchemy import select
        
        result = db.execute(
            select(Product).where(Product.business_id == business_id)
        )
        products = result.scalars().all()
        
        inventory_items = []
        low_stock_count = 0
        out_of_stock_count = 0
        total_value = 0
        
        for product in products:
            stock = getattr(product, 'stock_quantity', 0) or 0
            cost = getattr(product, 'cost_price', product.price * 0.6) or 0
            
            if stock <= 0:
                out_of_stock_count += 1
            elif stock <= 10:
                low_stock_count += 1
            
            item_value = stock * cost
            total_value += item_value
            
            inventory_items.append({
                "name": product.name,
                "sku": product.sku,
                "stock": stock,
                "cost": cost,
                "value": item_value,
                "status": "out_of_stock" if stock <= 0 else "low_stock" if stock <= 10 else "in_stock"
            })
        
        return {
            "summary": {
                "total_products": len(products),
                "total_value": total_value,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count
            },
            "items": inventory_items
        }
    
    async def _fetch_customer_data(
        self,
        db,
        business_id: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """Fetch customer analytics data"""
        from app.models.customer import Customer
        from sqlalchemy import select, func, and_
        
        conditions = [Customer.business_id == business_id]
        if start_date:
            conditions.append(Customer.created_at >= start_date)
        if end_date:
            conditions.append(Customer.created_at <= end_date)
        
        # Customer counts
        result = db.execute(
            select(func.count(Customer.id)).where(and_(*conditions))
        )
        total_customers = result.scalar() or 0
        
        # Top customers by spending
        top_result = db.execute(
            select(Customer)
            .where(Customer.business_id == business_id)
            .order_by(Customer.total_spent.desc())
            .limit(10)
        )
        top_customers = [
            {
                "name": c.name,
                "email": c.email,
                "total_spent": c.total_spent or 0,
                "total_orders": c.total_orders or 0
            }
            for c in top_result.scalars().all()
        ]
        
        return {
            "summary": {
                "total_customers": total_customers,
            },
            "top_customers": top_customers
        }
    
    async def _fetch_financial_data(
        self,
        db,
        business_id: str,
        year: int,
        month: Optional[int]
    ) -> Dict[str, Any]:
        """Fetch financial data for reporting"""
        # Simplified - in production this would aggregate payments, refunds, etc.
        return {
            "year": year,
            "month": month,
            "revenue": 0,
            "refunds": 0,
            "net_revenue": 0,
            "transactions": []
        }
    
    async def _generate_pdf_sales_report(
        self,
        data: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> BytesIO:
        """Generate PDF sales report"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            
            # Title
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2980b9')
            )
            elements.append(Paragraph("Sales Report", title_style))
            elements.append(Spacer(1, 0.25*inch))
            
            # Period
            period_text = f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
            elements.append(Paragraph(period_text, styles['Normal']))
            elements.append(Spacer(1, 0.5*inch))
            
            # Summary
            summary = data['summary']
            summary_data = [
                ["Metric", "Value"],
                ["Total Orders", str(summary['total_orders'])],
                ["Total Revenue", f"${summary['total_revenue']:,.2f}"],
                ["Average Order Value", f"${summary['avg_order_value']:,.2f}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.white)
            ]))
            
            elements.append(summary_table)
            elements.append(Spacer(1, 0.5*inch))
            
            # Daily breakdown
            if data['daily']:
                elements.append(Paragraph("Daily Breakdown", styles['Heading2']))
                elements.append(Spacer(1, 0.25*inch))
                
                daily_data = [["Date", "Orders", "Revenue"]]
                for day in data['daily'][-14:]:  # Last 14 days
                    daily_data.append([
                        day['date'],
                        str(day['orders']),
                        f"${day['revenue']:,.2f}"
                    ])
                
                daily_table = Table(daily_data, colWidths=[2*inch, 1.5*inch, 2*inch])
                daily_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                
                elements.append(daily_table)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            logger.warning("reportlab not installed, returning empty buffer")
            return BytesIO(b"PDF generation requires reportlab")
    
    async def _generate_pdf_inventory_report(self, data: Dict[str, Any]) -> BytesIO:
        """Generate PDF inventory report"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            
            # Title
            elements.append(Paragraph("Inventory Report", styles['Heading1']))
            elements.append(Spacer(1, 0.5*inch))
            
            # Summary
            summary = data['summary']
            summary_text = f"""
            <b>Total Products:</b> {summary['total_products']}<br/>
            <b>Total Inventory Value:</b> ${summary['total_value']:,.2f}<br/>
            <b>Low Stock Items:</b> {summary['low_stock_count']}<br/>
            <b>Out of Stock:</b> {summary['out_of_stock_count']}
            """
            elements.append(Paragraph(summary_text, styles['Normal']))
            elements.append(Spacer(1, 0.5*inch))
            
            # Items table
            if data['items']:
                items_data = [["Product", "SKU", "Stock", "Value", "Status"]]
                for item in data['items'][:50]:  # Top 50
                    items_data.append([
                        item['name'][:30],
                        item['sku'] or '-',
                        str(item['stock']),
                        f"${item['value']:,.2f}",
                        item['status'].replace('_', ' ').title()
                    ])
                
                items_table = Table(items_data, colWidths=[2*inch, 1*inch, 0.75*inch, 1*inch, 1*inch])
                items_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                ]))
                
                elements.append(items_table)
            
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            return BytesIO(b"PDF generation requires reportlab")
    
    async def _generate_pdf_customer_report(self, data: Dict[str, Any]) -> BytesIO:
        """Generate PDF customer report"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            
            elements.append(Paragraph("Customer Report", styles['Heading1']))
            elements.append(Spacer(1, 0.5*inch))
            elements.append(Paragraph(f"Total Customers: {data['summary']['total_customers']}", styles['Normal']))
            
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            return BytesIO(b"PDF generation requires reportlab")
    
    async def _generate_pdf_financial_report(
        self,
        data: Dict[str, Any],
        year: int,
        month: Optional[int]
    ) -> BytesIO:
        """Generate PDF financial report"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            
            period = f"{year}" if not month else f"{datetime(year, month, 1).strftime('%B %Y')}"
            elements = [
                Paragraph(f"Financial Summary - {period}", styles['Heading1'])
            ]
            
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            return BytesIO(b"PDF generation requires reportlab")
    
    async def _generate_excel_report(
        self,
        data: Dict[str, Any],
        title: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BytesIO:
        """Generate generic Excel report from data"""
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            
            buffer = BytesIO()
            wb = Workbook()
            ws = wb.active
            ws.title = title[:31]  # Excel sheet name limit
            
            # Title
            ws['A1'] = title
            ws['A1'].font = Font(size=18, bold=True, color='2980B9')
            
            # Period if provided
            row = 3
            if start_date and end_date:
                ws[f'A{row}'] = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                row += 2
            
            # Summary section
            if 'summary' in data:
                ws[f'A{row}'] = "Summary"
                ws[f'A{row}'].font = Font(bold=True)
                row += 1
                
                for key, value in data['summary'].items():
                    ws[f'A{row}'] = key.replace('_', ' ').title()
                    ws[f'B{row}'] = value if not isinstance(value, float) else f"${value:,.2f}"
                    row += 1
                row += 1
            
            # Data sections
            for section_name, section_data in data.items():
                if section_name == 'summary' or not isinstance(section_data, list) or not section_data:
                    continue
                
                ws[f'A{row}'] = section_name.replace('_', ' ').title()
                ws[f'A{row}'].font = Font(bold=True)
                row += 1
                
                # Headers
                headers = list(section_data[0].keys())
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=row, column=col, value=header.replace('_', ' ').title())
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color='2980B9', end_color='2980B9', fill_type='solid')
                    cell.font = Font(bold=True, color='FFFFFF')
                row += 1
                
                # Data rows
                for item in section_data:
                    for col, header in enumerate(headers, 1):
                        ws.cell(row=row, column=col, value=item.get(header, ''))
                    row += 1
                row += 1
            
            # Auto-width columns
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
            
            wb.save(buffer)
            buffer.seek(0)
            return buffer
            
        except ImportError:
            return BytesIO(b"Excel generation requires openpyxl and pandas")
    
    async def _generate_excel_from_rows(
        self,
        rows: List[Dict[str, Any]],
        title: str
    ) -> BytesIO:
        """Generate Excel file from list of row dictionaries"""
        try:
            import pandas as pd
            
            buffer = BytesIO()
            df = pd.DataFrame(rows)
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=title[:31], index=False)
                
                # Get worksheet to format
                ws = writer.sheets[title[:31]]
                
                # Auto-width columns
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    ws.column_dimensions[column_letter].width = min(max_length + 2, 50)
            
            buffer.seek(0)
            return buffer
            
        except ImportError:
            return BytesIO(b"Excel generation requires pandas and openpyxl")


# Global instance
report_service = ReportService()
