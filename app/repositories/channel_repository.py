from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.storage_channel import StorageChannel


class ChannelRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        telegram_chat_id: int,
        name: str,
    ) -> StorageChannel:

        channel = StorageChannel(
            telegram_chat_id=telegram_chat_id,
            name=name,
            status="ACTIVE",
        )

        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)

        return channel

    def get_active(self) -> list[StorageChannel]:

        result = self.db.execute(
            select(StorageChannel).where(
                StorageChannel.status == "ACTIVE"
            )
        )

        return list(result.scalars().all())

    def get_by_id(
        self,
        channel_id: str,
    ) -> StorageChannel | None:

        return self.db.get(
            StorageChannel,
            channel_id,
        )

    def get_by_chat_id(
        self,
        chat_id: int,
    ) -> StorageChannel | None:

        result = self.db.execute(
            select(StorageChannel).where(
                StorageChannel.telegram_chat_id == chat_id
            )
        )

        return result.scalar_one_or_none()
