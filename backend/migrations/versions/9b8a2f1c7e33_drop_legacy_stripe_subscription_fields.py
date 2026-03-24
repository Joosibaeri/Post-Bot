"""drop_legacy_stripe_subscription_fields

Revision ID: 9b8a2f1c7e33
Revises: 5c2f9b7a1d44
Create Date: 2026-03-24 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b8a2f1c7e33"
down_revision: Union[str, Sequence[str], None] = "5c2f9b7a1d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop legacy Stripe subscription fields after Paystack migration."""
    op.drop_index("idx_subscriptions_customer", table_name="subscriptions")
    op.drop_column("subscriptions", "stripe_subscription_id")
    op.drop_column("subscriptions", "stripe_customer_id")


def downgrade() -> None:
    """Restore legacy Stripe subscription fields for rollback safety."""
    op.add_column("subscriptions", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.add_column("subscriptions", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.create_index("idx_subscriptions_customer", "subscriptions", ["stripe_customer_id"], unique=False)
