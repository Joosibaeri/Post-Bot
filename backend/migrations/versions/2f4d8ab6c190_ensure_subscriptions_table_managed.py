"""ensure_subscriptions_table_managed

Revision ID: 2f4d8ab6c190
Revises: 9b8a2f1c7e33
Create Date: 2026-03-24 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2f4d8ab6c190"
down_revision: Union[str, Sequence[str], None] = "9b8a2f1c7e33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure subscriptions table exists in migration chain and is schema-complete."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            paystack_customer_code VARCHAR(255) UNIQUE,
            paystack_subscription_code VARCHAR(255) UNIQUE,
            paystack_email_token VARCHAR(255),
            paystack_authorization_code VARCHAR(255),
            plan_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'inactive',
            current_period_start BIGINT,
            current_period_end BIGINT,
            cancel_at_period_end INTEGER DEFAULT 0,
            created_at BIGINT,
            updated_at BIGINT
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_paystack_customer ON subscriptions(paystack_customer_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_paystack_subscription ON subscriptions(paystack_subscription_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)")


def downgrade() -> None:
    """No-op downgrade to avoid destructive table drops of subscription data."""
    pass
