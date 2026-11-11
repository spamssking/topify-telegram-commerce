from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.repositories.channel_repository import ChannelRepository
from app.schemas.storage_channel import (
    StorageChannelCreate,
    StorageChannelResponse,
)


router = APIRouter(
    prefix="/api/storage/channels",
    tags=["Storage Channels"],
)


@router.post(
    "",
    response_model=StorageChannelResponse,
)
def create_channel(
    data: StorageChannelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = ChannelRepository(db)

    return repository.create(
        telegram_chat_id=data.telegram_chat_id,
        name=data.name,
    )


@router.get(
    "",
    response_model=list[StorageChannelResponse],
)
def get_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = ChannelRepository(db)

    return repository.get_active()
