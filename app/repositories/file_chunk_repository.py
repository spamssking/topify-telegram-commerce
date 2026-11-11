from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.file_chunk import FileChunk


class FileChunkRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        chunk: FileChunk,
    ) -> FileChunk:

        self.db.add(chunk)
        self.db.flush()
        self.db.refresh(chunk)

        return chunk

    def get_by_file(
        self,
        file_id: str,
    ) -> list[FileChunk]:

        result = self.db.execute(
            select(FileChunk)
            .where(
                FileChunk.file_id == file_id,
            )
            .order_by(
                FileChunk.chunk_index.asc()
            )
        )

        return list(result.scalars().all())

    def get_by_file_and_index(
        self,
        file_id: str,
        chunk_index: int,
    ) -> FileChunk | None:

        result = self.db.execute(
            select(FileChunk).where(
                FileChunk.file_id == file_id,
                FileChunk.chunk_index == chunk_index,
            )
        )

        return result.scalar_one_or_none()

    def delete_for_file(
        self,
        file_id: str,
    ) -> None:

        chunks = self.get_by_file(file_id)

        for chunk in chunks:
            self.db.delete(chunk)

        self.db.flush()
