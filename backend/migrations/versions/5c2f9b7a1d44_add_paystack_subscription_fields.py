"""add_paystack_subscription_fields

Revision ID: 5c2f9b7a1d44
Revises: 88922ef82cf0
Create Date: 2026-03-24 05:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c2f9b7a1d44'
down_revision: Union[str, Sequence[str], None] = '88922ef82cf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Paystack subscription fields while retaining legacy Stripe columns."""
    op.add_column('subscriptions', sa.Column('paystack_customer_code', sa.String(length=255), nullable=True))
    op.add_column('subscriptions', sa.Column('paystack_subscription_code', sa.String(length=255), nullable=True))
    op.add_column('subscriptions', sa.Column('paystack_email_token', sa.String(length=255), nullable=True))
    op.add_column('subscriptions', sa.Column('paystack_authorization_code', sa.String(length=255), nullable=True))
    op.create_index('idx_subscriptions_paystack_customer', 'subscriptions', ['paystack_customer_code'], unique=False)
    op.create_index('idx_subscriptions_paystack_subscription', 'subscriptions', ['paystack_subscription_code'], unique=False)


def downgrade() -> None:
    """Remove Paystack subscription fields."""
    op.drop_index('idx_subscriptions_paystack_subscription', table_name='subscriptions')
    op.drop_index('idx_subscriptions_paystack_customer', table_name='subscriptions')
    op.drop_column('subscriptions', 'paystack_authorization_code')
    op.drop_column('subscriptions', 'paystack_email_token')
    op.drop_column('subscriptions', 'paystack_subscription_code')
    op.drop_column('subscriptions', 'paystack_customer_code')