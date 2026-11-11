from pydantic import BaseModel, ConfigDict


class StorageChannelCreate(BaseModel):
    telegram_chat_id: int
    name: str


class StorageChannelResponse(BaseModel):
    id: str
    telegram_chat_id: int
    name: str
    status: str

    model_config = ConfigDict(
        from_attributes=True,
    )
