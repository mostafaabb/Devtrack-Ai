"""Add enterprise features tables

Revision ID: enterprise_features_001
Revises: 
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = 'enterprise_features_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════
    # PAYMENTS
    # ═══════════════════════════════════════════════════════════════════
    
    op.create_table(
        'payments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('booking_id', UUID(as_uuid=True), sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('payment_number', sa.String(50), unique=True, nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('method', sa.String(50), default='card'),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True, index=True),
        sa.Column('stripe_charge_id', sa.String(255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=True),
        sa.Column('checkout_url', sa.String(500), nullable=True),
        sa.Column('checkout_expires_at', sa.DateTime, nullable=True),
        sa.Column('card_brand', sa.String(50), nullable=True),
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_exp_month', sa.Integer, nullable=True),
        sa.Column('card_exp_year', sa.Integer, nullable=True),
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('failure_message', sa.Text, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', JSON, default=dict),
        sa.Column('receipt_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('paid_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'refunds',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('payment_id', UUID(as_uuid=True), sa.ForeignKey('payments.id'), nullable=False),
        sa.Column('refund_number', sa.String(50), unique=True, nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('stripe_refund_id', sa.String(255), nullable=True),
        sa.Column('metadata', JSON, default=dict),
        sa.Column('initiated_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'customer_payment_methods',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('card_brand', sa.String(50), nullable=True),
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_exp_month', sa.Integer, nullable=True),
        sa.Column('card_exp_year', sa.Integer, nullable=True),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ═══════════════════════════════════════════════════════════════════
    # COUPONS & PROMOTIONS
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        'coupons',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('discount_type', sa.String(50), default='percentage'),
        sa.Column('discount_value', sa.Float, nullable=False),
        sa.Column('max_discount_amount', sa.Float, nullable=True),
        sa.Column('minimum_order_amount', sa.Float, default=0),
        sa.Column('minimum_quantity', sa.Integer, default=0),
        sa.Column('usage_limit', sa.Integer, nullable=True),
        sa.Column('usage_limit_per_customer', sa.Integer, nullable=True),
        sa.Column('times_used', sa.Integer, default=0),
        sa.Column('starts_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('applies_to', sa.String(50), default='all'),
        sa.Column('applicable_ids', JSON, default=list),
        sa.Column('excluded_ids', JSON, default=list),
        sa.Column('customer_ids', JSON, default=list),
        sa.Column('first_order_only', sa.Boolean, default=False),
        sa.Column('buy_quantity', sa.Integer, nullable=True),
        sa.Column('get_quantity', sa.Integer, nullable=True),
        sa.Column('get_product_ids', JSON, default=list),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('is_automatic', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'coupon_usages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('coupon_id', UUID(as_uuid=True), sa.ForeignKey('coupons.id'), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('discount_applied', sa.Float, nullable=False),
        sa.Column('order_subtotal', sa.Float, nullable=True),
        sa.Column('used_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'promotions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('banner_image', sa.String(500), nullable=True),
        sa.Column('discount_type', sa.String(50), default='percentage'),
        sa.Column('discount_value', sa.Float, nullable=False),
        sa.Column('product_ids', JSON, default=list),
        sa.Column('category_ids', JSON, default=list),
        sa.Column('starts_at', sa.DateTime, nullable=False),
        sa.Column('ends_at', sa.DateTime, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_featured', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ═══════════════════════════════════════════════════════════════════
    # INVENTORY
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        'suppliers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=True),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('payment_terms', sa.String(100), nullable=True),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('lead_time_days', sa.Integer, default=7),
        sa.Column('rating', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'locations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('operating_hours', JSON, default=dict),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_primary', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'product_inventory',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False, unique=True),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('quantity_on_hand', sa.Integer, default=0),
        sa.Column('quantity_reserved', sa.Integer, default=0),
        sa.Column('quantity_available', sa.Integer, default=0),
        sa.Column('reorder_point', sa.Integer, default=10),
        sa.Column('reorder_quantity', sa.Integer, default=50),
        sa.Column('safety_stock', sa.Integer, default=5),
        sa.Column('max_stock', sa.Integer, nullable=True),
        sa.Column('cost_price', sa.Float, default=0),
        sa.Column('last_cost_price', sa.Float, nullable=True),
        sa.Column('last_counted_at', sa.DateTime, nullable=True),
        sa.Column('last_restocked_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'stock_movements',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('movement_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('quantity_before', sa.Integer, nullable=False),
        sa.Column('quantity_after', sa.Integer, nullable=False),
        sa.Column('unit_cost', sa.Float, nullable=True),
        sa.Column('total_cost', sa.Float, nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', UUID(as_uuid=True), nullable=True),
        sa.Column('from_location_id', UUID(as_uuid=True), nullable=True),
        sa.Column('to_location_id', UUID(as_uuid=True), nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'purchase_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('supplier_id', UUID(as_uuid=True), sa.ForeignKey('suppliers.id'), nullable=False),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('po_number', sa.String(50), unique=True, nullable=False),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('subtotal', sa.Float, default=0),
        sa.Column('tax', sa.Float, default=0),
        sa.Column('shipping', sa.Float, default=0),
        sa.Column('total', sa.Float, default=0),
        sa.Column('currency', sa.String(10), default='USD'),
        sa.Column('order_date', sa.DateTime, nullable=True),
        sa.Column('expected_date', sa.DateTime, nullable=True),
        sa.Column('received_date', sa.DateTime, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'purchase_order_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('purchase_order_id', UUID(as_uuid=True), sa.ForeignKey('purchase_orders.id'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('quantity_ordered', sa.Integer, nullable=False),
        sa.Column('quantity_received', sa.Integer, default=0),
        sa.Column('unit_cost', sa.Float, nullable=False),
        sa.Column('total_cost', sa.Float, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'inventory_alerts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('current_quantity', sa.Integer, nullable=False),
        sa.Column('threshold_quantity', sa.Integer, nullable=True),
        sa.Column('is_resolved', sa.Boolean, default=False),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('resolved_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ═══════════════════════════════════════════════════════════════════
    # LOYALTY PROGRAM
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        'loyalty_programs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False, unique=True),
        sa.Column('name', sa.String(255), default='Rewards Program'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('points_per_currency', sa.Float, default=1.0),
        sa.Column('currency_per_point', sa.Float, default=0.01),
        sa.Column('min_points_redeem', sa.Integer, default=100),
        sa.Column('points_expire', sa.Boolean, default=False),
        sa.Column('points_expire_days', sa.Integer, default=365),
        sa.Column('signup_bonus_points', sa.Integer, default=0),
        sa.Column('referral_points_referrer', sa.Integer, default=0),
        sa.Column('referral_points_referee', sa.Integer, default=0),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'loyalty_tiers',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('program_id', UUID(as_uuid=True), sa.ForeignKey('loyalty_programs.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('color', sa.String(20), default='#888888'),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('min_points', sa.Integer, default=0),
        sa.Column('min_spent', sa.Float, default=0),
        sa.Column('points_multiplier', sa.Float, default=1.0),
        sa.Column('discount_percentage', sa.Float, default=0),
        sa.Column('free_shipping', sa.Boolean, default=False),
        sa.Column('priority_support', sa.Boolean, default=False),
        sa.Column('exclusive_access', sa.Boolean, default=False),
        sa.Column('extra_benefits', JSON, default=list),
        sa.Column('tier_order', sa.Integer, default=1),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'loyalty_rewards',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('program_id', UUID(as_uuid=True), sa.ForeignKey('loyalty_programs.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('points_cost', sa.Integer, nullable=False),
        sa.Column('reward_type', sa.String(50), nullable=False),
        sa.Column('reward_value', sa.Float, nullable=True),
        sa.Column('reward_product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('min_tier_id', UUID(as_uuid=True), sa.ForeignKey('loyalty_tiers.id'), nullable=True),
        sa.Column('min_order_amount', sa.Float, default=0),
        sa.Column('stock_quantity', sa.Integer, nullable=True),
        sa.Column('times_redeemed', sa.Integer, default=0),
        sa.Column('starts_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_featured', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'customer_loyalty',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=False, unique=True),
        sa.Column('program_id', UUID(as_uuid=True), sa.ForeignKey('loyalty_programs.id'), nullable=False),
        sa.Column('tier_id', UUID(as_uuid=True), sa.ForeignKey('loyalty_tiers.id'), nullable=True),
        sa.Column('points_balance', sa.Integer, default=0),
        sa.Column('points_earned_total', sa.Integer, default=0),
        sa.Column('points_redeemed_total', sa.Integer, default=0),
        sa.Column('points_expired_total', sa.Integer, default=0),
        sa.Column('total_spent', sa.Float, default=0),
        sa.Column('total_orders', sa.Integer, default=0),
        sa.Column('referral_code', sa.String(20), unique=True, nullable=True),
        sa.Column('referred_by', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('referral_count', sa.Integer, default=0),
        sa.Column('joined_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('tier_updated_at', sa.DateTime, nullable=True),
        sa.Column('last_activity_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'loyalty_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('customer_loyalty_id', UUID(as_uuid=True), sa.ForeignKey('customer_loyalty.id'), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('points', sa.Integer, nullable=False),
        sa.Column('balance_after', sa.Integer, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('reference_type', sa.String(50), nullable=True),
        sa.Column('reference_id', UUID(as_uuid=True), nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_expired', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ═══════════════════════════════════════════════════════════════════
    # TEAM & PERMISSIONS
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        'permissions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('role_type', sa.String(50), default='custom'),
        sa.Column('permissions', JSON, default=list),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'team_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('title', sa.String(100), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('work_schedule', JSON, default=dict),
        sa.Column('extra_permissions', JSON, default=list),
        sa.Column('restricted_permissions', JSON, default=list),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('joined_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'team_invites',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('invite_token', sa.String(255), unique=True, nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('invited_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('responded_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'activity_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('old_values', JSON, nullable=True),
        sa.Column('new_values', JSON, nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ═══════════════════════════════════════════════════════════════════
    # MARKETING CAMPAIGNS
    # ═══════════════════════════════════════════════════════════════════

    op.create_table(
        'email_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('template_type', sa.String(50), default='email'),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('html_content', sa.Text, nullable=True),
        sa.Column('variables', JSON, default=list),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'campaigns',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('campaign_type', sa.String(50), default='email'),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('html_content', sa.Text, nullable=True),
        sa.Column('template_id', UUID(as_uuid=True), sa.ForeignKey('email_templates.id'), nullable=True),
        sa.Column('from_name', sa.String(255), nullable=True),
        sa.Column('from_email', sa.String(255), nullable=True),
        sa.Column('reply_to', sa.String(255), nullable=True),
        sa.Column('segment_rules', JSON, default=dict),
        sa.Column('customer_tags', JSON, default=list),
        sa.Column('exclude_tags', JSON, default=list),
        sa.Column('trigger_type', sa.String(50), default='manual'),
        sa.Column('scheduled_at', sa.DateTime, nullable=True),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('total_recipients', sa.Integer, default=0),
        sa.Column('sent_count', sa.Integer, default=0),
        sa.Column('delivered_count', sa.Integer, default=0),
        sa.Column('opened_count', sa.Integer, default=0),
        sa.Column('clicked_count', sa.Integer, default=0),
        sa.Column('bounced_count', sa.Integer, default=0),
        sa.Column('unsubscribed_count', sa.Integer, default=0),
        sa.Column('revenue_attributed', sa.Float, default=0),
        sa.Column('orders_attributed', sa.Integer, default=0),
        sa.Column('track_opens', sa.Boolean, default=True),
        sa.Column('track_clicks', sa.Boolean, default=True),
        sa.Column('is_ab_test', sa.Boolean, default=False),
        sa.Column('ab_variant', sa.String(10), nullable=True),
        sa.Column('ab_parent_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'campaign_recipients',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('delivered_at', sa.DateTime, nullable=True),
        sa.Column('opened_at', sa.DateTime, nullable=True),
        sa.Column('clicked_at', sa.DateTime, nullable=True),
        sa.Column('open_count', sa.Integer, default=0),
        sa.Column('click_count', sa.Integer, default=0),
        sa.Column('clicked_links', JSON, default=list),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'campaign_links',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=False),
        sa.Column('original_url', sa.String(2000), nullable=False),
        sa.Column('tracking_code', sa.String(50), unique=True, nullable=False),
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('click_count', sa.Integer, default=0),
        sa.Column('unique_clicks', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'unsubscribes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('business_id', UUID(as_uuid=True), sa.ForeignKey('businesses.id'), nullable=False),
        sa.Column('customer_id', UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('campaign_id', UUID(as_uuid=True), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('unsubscribed_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('unsubscribes')
    op.drop_table('campaign_links')
    op.drop_table('campaign_recipients')
    op.drop_table('campaigns')
    op.drop_table('email_templates')
    op.drop_table('activity_logs')
    op.drop_table('team_invites')
    op.drop_table('team_members')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('loyalty_transactions')
    op.drop_table('customer_loyalty')
    op.drop_table('loyalty_rewards')
    op.drop_table('loyalty_tiers')
    op.drop_table('loyalty_programs')
    op.drop_table('inventory_alerts')
    op.drop_table('purchase_order_items')
    op.drop_table('purchase_orders')
    op.drop_table('stock_movements')
    op.drop_table('product_inventory')
    op.drop_table('locations')
    op.drop_table('suppliers')
    op.drop_table('promotions')
    op.drop_table('coupon_usages')
    op.drop_table('coupons')
    op.drop_table('customer_payment_methods')
    op.drop_table('refunds')
    op.drop_table('payments')
