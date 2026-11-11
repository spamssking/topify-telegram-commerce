import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    Boolean,
    Integer,

)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class File(Base):
    __tablename__ = "files"

    __table_args__ = (
        CheckConstraint(
            "size > 0",
            name="ck_files_size_positive",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    storage_channel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("storage_channels.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    telegram_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    telegram_file_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    storage_backend: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LOCAL_BOT",
        server_default="LOCAL_BOT",
    )


    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    telegram_message_id: Mapped[int | None] = mapped_column(
    BigInteger,
    nullable=True,
    )

    telegram_file_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    is_chunked: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default="false",
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )


    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    thumbnail_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
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

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    user = relationship(
        "User",
        back_populates="files",
    )

    storage_channel = relationship(
        "StorageChannel",
        back_populates="files",
    )

    chunks = relationship(
    "FileChunk",
    back_populates="file",
    cascade="all, delete-orphan",
    order_by="FileChunk.chunk_index",
    )

