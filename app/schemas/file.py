from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    id: str
    name: str
    mime_type: str | None
    size: int
    sha256: str
    status: str
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class FileListResponse(BaseModel):
    items: list[FileResponse]
    page: int
    page_size: int
    total: int