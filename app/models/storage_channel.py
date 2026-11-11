import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StorageChannel(Base):
    __tablename__ = "storage_channels"

    __table_args__ = (
        CheckConstraint(
            "priority >= 0",
            name="ck_storage_channels_priority_non_negative",
        ),
        CheckConstraint(
            "weight > 0",
            name="ck_storage_channels_weight_positive",
        ),
        CheckConstraint(
            "used_bytes >= 0",
            name="ck_storage_channels_used_bytes_non_negative",
        ),
        CheckConstraint(
            "failure_count >= 0",
            name="ck_storage_channels_failure_count_non_negative",
        ),
        CheckConstraint(
            "capacity_bytes IS NULL OR capacity_bytes > 0",
            name="ck_storage_channels_capacity_positive",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
        index=True,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    capacity_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    used_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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

    files = relationship(
        "File",
        back_populates="storage_channel",
    )
