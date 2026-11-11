"""seed default plans

Revision ID: 40f9626217ec
Revises: 8f3c2a1d5b70
Create Date: 2026-09-12 02:00:54.780527

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '40f9626217ec'
down_revision: Union[str, Sequence[str], None] = '671f93b04a17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FREE_PLAN_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    plans = sa.table(
        "plans",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("storage_quota_bytes", sa.BigInteger),
        sa.column("max_file_size_bytes", sa.BigInteger),
        sa.column("max_files", sa.Integer),
        sa.column("thumbnail_enabled", sa.Boolean),
        sa.column("price", sa.BigInteger),
        sa.column("currency", sa.String),
        sa.column("billing_interval", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
    )

    op.bulk_insert(
        plans,
        [
            {
                "id": FREE_PLAN_ID,
                "code": "FREE",
                "name": "Free",
                "description": "Free storage plan for new users.",
                "storage_quota_bytes": 5 * 1024 * 1024 * 1024,
                "max_file_size_bytes": 2 * 1024 * 1024 * 1024,
                "max_files": None,
                "thumbnail_enabled": True,
                "price": 0,
                "currency": "NGN",
                "billing_interval": None,
                "sort_order": 0,
                "is_active": True,
                "is_default": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM plans WHERE id = :plan_id"
        ).bindparams(
            plan_id=FREE_PLAN_ID
        )
    )