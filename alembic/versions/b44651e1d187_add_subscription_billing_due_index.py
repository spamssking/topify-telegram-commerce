"""add subscription billing due index

Revision ID: b44651e1d187
Revises: 95cf410c3372
Create Date: 2026-09-29 09:01:43.313515

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = 'b44651e1d187'
down_revision: Union[str, Sequence[str], None] = '95cf410c3372'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_subscriptions_billing_due",
        "subscriptions",
        ["status", "auto_renew", "next_billing_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscriptions_billing_due",
        table_name="subscriptions",
    )
