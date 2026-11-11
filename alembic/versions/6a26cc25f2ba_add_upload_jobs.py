"""add upload jobs

Revision ID: 6a26cc25f2ba
Revises: f66aa857ee16
Create Date: 2026-09-17 06:32:40.602923

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6a26cc25f2ba"
down_revision: Union[str, Sequence[str], None] = "f66aa857ee16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # =====================================================
    # FILES
    # =====================================================

    op.add_column(
        "files",
        sa.Column(
            "storage_backend",
            sa.String(length=50),
            server_default="LOCAL_BOT",
            nullable=False,
        ),
    )

    # =====================================================
    # UPLOAD JOBS
    # =====================================================

    op.create_table(
        "upload_jobs",

        # -------------------------------------------------
        # ID
        # -------------------------------------------------

        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),

        # -------------------------------------------------
        # USER
        # -------------------------------------------------

        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
        ),

        # -------------------------------------------------
        # RESULTING FILE
        # -------------------------------------------------

        sa.Column(
            "file_id",
            sa.String(length=36),
            nullable=True,
        ),

        # -------------------------------------------------
        # STAGING
        # -------------------------------------------------

        sa.Column(
            "staging_path",
            sa.Text(),
            nullable=False,
        ),

        # -------------------------------------------------
        # ORIGINAL FILE INFORMATION
        # -------------------------------------------------

        sa.Column(
            "original_filename",
            sa.String(length=500),
            nullable=False,
        ),

        sa.Column(
            "file_size",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "mime_type",
            sa.String(length=255),
            nullable=True,
        ),

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        sa.Column(
            "status",
            sa.String(length=30),
            server_default="QUEUED",
            nullable=False,
        ),

        # -------------------------------------------------
        # RETRIES
        # -------------------------------------------------

        sa.Column(
            "attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),

        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),

        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        # -------------------------------------------------
        # ERROR
        # -------------------------------------------------

        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),

        # -------------------------------------------------
        # STORAGE BACKEND
        # -------------------------------------------------

        sa.Column(
            "storage_backend",
            sa.String(length=50),
            server_default="LOCAL_BOT",
            nullable=False,
        ),

        # -------------------------------------------------
        # TIMESTAMPS
        # -------------------------------------------------

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        # -------------------------------------------------
        # PRIMARY KEY
        # -------------------------------------------------

        sa.PrimaryKeyConstraint(
            "id"
        ),

        # -------------------------------------------------
        # FOREIGN KEYS
        # -------------------------------------------------

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="SET NULL",
        ),
    )

    # =====================================================
    # INDEXES
    # =====================================================

    op.create_index(
        "ix_upload_jobs_user_id",
        "upload_jobs",
        ["user_id"],
    )

    op.create_index(
        "ix_upload_jobs_file_id",
        "upload_jobs",
        ["file_id"],
    )

    op.create_index(
        "ix_upload_jobs_status",
        "upload_jobs",
        ["status"],
    )

    op.create_index(
        "ix_upload_jobs_next_attempt_at",
        "upload_jobs",
        ["next_attempt_at"],
    )


def downgrade() -> None:

    # =====================================================
    # UPLOAD JOBS
    # =====================================================

    op.drop_index(
        "ix_upload_jobs_next_attempt_at",
        table_name="upload_jobs",
    )

    op.drop_index(
        "ix_upload_jobs_status",
        table_name="upload_jobs",
    )

    op.drop_index(
        "ix_upload_jobs_file_id",
        table_name="upload_jobs",
    )

    op.drop_index(
        "ix_upload_jobs_user_id",
        table_name="upload_jobs",
    )

    op.drop_table(
        "upload_jobs"
    )

    # =====================================================
    # FILES
    # =====================================================

    op.drop_column(
        "files",
        "storage_backend",
    )
