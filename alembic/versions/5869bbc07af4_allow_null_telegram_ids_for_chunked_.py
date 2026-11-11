"""allow null telegram ids for chunked files

Revision ID: YOUR_NEW_REVISION
Revises: 9ec75dc03081
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op


revision: str = "5869bbc07af4"
down_revision: Union[str, Sequence[str], None] = "9ec75dc03081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "files",
        "telegram_message_id",
        nullable=True,
    )

    op.alter_column(
        "files",
        "telegram_file_id",
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "files",
        "telegram_message_id",
        nullable=False,
    )

    op.alter_column(
        "files",
        "telegram_file_id",
        nullable=False,
    )
