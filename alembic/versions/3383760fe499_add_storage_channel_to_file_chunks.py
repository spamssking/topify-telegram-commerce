"""add storage channel to file chunks

Revision ID: 3383760fe499
Revises: 9ec75dc03081
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3383760fe499"

down_revision: Union[str, Sequence[str], None] = "9ec75dc03081"

branch_labels = None
depends_on = None


def upgrade() -> None:

    op.add_column(
        "file_chunks",
        sa.Column(
            "storage_channel_id",
            sa.String(length=36),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_file_chunks_storage_channel_id",
        "file_chunks",
        ["storage_channel_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_file_chunks_storage_channel_id",
        "file_chunks",
        "storage_channels",
        ["storage_channel_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:

    op.drop_constraint(
        "fk_file_chunks_storage_channel_id",
        "file_chunks",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_file_chunks_storage_channel_id",
        table_name="file_chunks",
    )

    op.drop_column(
        "file_chunks",
        "storage_channel_id",
    )
