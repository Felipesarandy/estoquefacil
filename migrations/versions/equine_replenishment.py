"""Adiciona reposição sem alterar nem apagar tabelas existentes."""
from alembic import op
import sqlalchemy as sa

revision = 'equine_replenishment'
down_revision = 'd2b9e292d1e5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('replenishment_policies',
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), primary_key=True),
        sa.Column('weekly_consumption', sa.Numeric(10, 3), nullable=False),
        sa.Column('lead_days', sa.Integer(), nullable=False),
        sa.Column('safety_days', sa.Integer(), nullable=False),
        sa.Column('order_quantity', sa.Numeric(10, 3), nullable=False),
        sa.CheckConstraint('weekly_consumption > 0 AND lead_days >= 0 AND safety_days >= 0 AND order_quantity > 0'))
    op.create_table('purchase_orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 3), nullable=False),
        sa.Column('expected_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('received_at', sa.DateTime()),
        sa.Column('received_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.CheckConstraint('quantity > 0'),
        sa.CheckConstraint("status IN ('pending', 'received', 'cancelled')"))


def downgrade():
    op.drop_table('purchase_orders')
    op.drop_table('replenishment_policies')
