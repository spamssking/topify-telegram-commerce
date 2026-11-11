import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FileChunk(Base):

    __tablename__ = "file_chunks"

    __table_args__ = (
        UniqueConstraint(
            "file_id",
            "chunk_index",
            name="uq_file_chunks_file_index",
        ),
    )

    # -----------------------------------------------------
    # ID
    # -----------------------------------------------------

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # -----------------------------------------------------
    # PARENT FILE
    # -----------------------------------------------------

    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # STORAGE CHANNEL
    # -----------------------------------------------------

    storage_channel_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "storage_channels.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

#    storage_channel_id: Mapped[str] = mapped_column(
#        String(36),
#        ForeignKey(
#            "storage_channels.id",
#            ondelete="RESTRICT",
#        ),
#        nullable=False,
#        index=True,
#    )


    # -----------------------------------------------------
    # CHUNK ORDER
    # -----------------------------------------------------

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # -----------------------------------------------------
    # CHUNK SIZE
    # -----------------------------------------------------

    size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # -----------------------------------------------------
    # CHUNK HASH
    # -----------------------------------------------------

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # -----------------------------------------------------
    # TELEGRAM MESSAGE
    # -----------------------------------------------------

    telegram_message_id: Mapped[int] = mapped_column(
        nullable=False,
    )

    # -----------------------------------------------------
    # TELEGRAM FILE
    # -----------------------------------------------------

    telegram_file_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # -----------------------------------------------------
    # CREATED
    # -----------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # -----------------------------------------------------
    # RELATIONSHIPS
    # -----------------------------------------------------

    file = relationship(
        "File",
        back_populates="chunks",
    )

    storage_channel = relationship(
        "StorageChannel",
    )