# app/schemas/upload_job.py

from pydantic import BaseModel


class UploadJobResponse(BaseModel):

    id: str

    status: str

    filename: str

    size: int

    attempts: int

    error: str | None = None

    file_id: str | None = None
