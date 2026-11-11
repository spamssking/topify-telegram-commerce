# app/models/upload_job.py

import uuid

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.database import Base


class UploadJob(Base):

    __tablename__ = "upload_jobs"

    # =====================================================
    # ID
    # =====================================================

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # =====================================================
    # USER
    # =====================================================

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # RESULTING FILE
    # =====================================================

    file_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "files.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # =====================================================
    # STAGING
    # =====================================================

    staging_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # =====================================================
    # ORIGINAL FILE INFORMATION
    # =====================================================

    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # =====================================================
    # JOB STATUS
    # =====================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="QUEUED",
        server_default="QUEUED",
        index=True,
    )

    # =====================================================
    # RETRIES
    # =====================================================

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )

    next_attempt_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # =====================================================
    # ERROR INFORMATION
    # =====================================================

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # =====================================================
    # STORAGE BACKEND
    # =====================================================

    storage_backend: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LOCAL_BOT",
        server_default="LOCAL_BOT",
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    completed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    user = relationship(
        "User",
    )

    file = relationship(
        "File",
    )
