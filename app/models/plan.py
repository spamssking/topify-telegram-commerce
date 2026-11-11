import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    __table_args__ = (
        CheckConstraint(
            "storage_quota_bytes > 0",
            name="ck_plans_storage_quota_positive",
        ),
        CheckConstraint(
            "max_file_size_bytes > 0",
            name="ck_plans_max_file_size_positive",
        ),
        CheckConstraint(
            "max_files IS NULL OR max_files > 0",
            name="ck_plans_max_files_positive",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_plans_price_non_negative",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Bytes.
    storage_quota_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Maximum size of one uploaded file.
    max_file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # NULL means unlimited.
    max_files: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    thumbnail_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Smallest currency unit.
    #
    # Example:
    # NGN 5,000 = 500000 kobo.
    price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="NGN",
        server_default="NGN",
    )

    # NULL for FREE.
    billing_interval: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # Exactly one plan should normally be the default.
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    users = relationship(
        "User",
        back_populates="plan",
    )

    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
    )

    payments = relationship(
        "Payment",
        back_populates="plan",
    )
