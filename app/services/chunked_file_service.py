import hashlib
import os
import tempfile


from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.file import File
from app.models.file_chunk import FileChunk
from app.models.user import User
from app.repositories.channel_repository import ChannelRepository
from app.repositories.file_chunk_repository import FileChunkRepository
from app.repositories.file_repository import FileRepository
from app.services.channel_selector import ChannelSelector
from app.services.telegram_storage import (
    TelegramStorage,
    TelegramStorageError,
)


class ChunkedFileService:

    def __init__(self, db: Session):

        self.db = db

        self.file_repository = FileRepository(
            db
        )

        self.chunk_repository = (
            FileChunkRepository(db)
        )

        self.channel_repository = (
            ChannelRepository(db)
        )

        self.channel_selector = ChannelSelector()

        self.telegram = TelegramStorage()

    async def upload(
        self,
        upload: UploadFile,
        user: User,
        file_size: int,
        chunk_size: int,
    ) -> File:

        if file_size <= 0:
            raise ValueError(
                "Uploaded file is empty."
            )

        if file_size <= chunk_size:
            raise ValueError(
                "Chunked upload was requested "
                "for a file that does not need chunking."
            )

        channels = (
            self.channel_repository.get_active()
        )

        channel = self.channel_selector.select(
            channels
        )

        filename = upload.filename or "file"

        # Create parent file record first.
        file_record = File(
            user_id=user.id,
            storage_channel_id=channel.id,
            name=filename,
            mime_type=upload.content_type,
            size=file_size,
            sha256="",
            status="UPLOADING",
            is_chunked=True,
            chunk_count=0,
        )

        self.db.add(file_record)
        self.db.flush()
        self.db.refresh(file_record)

        complete_hash = hashlib.sha256()

        uploaded_telegram_messages = []

        chunk_index = 0
        total_size = 0

        try:

            while True:

                chunk_bytes = await upload.read(
                    chunk_size
                )

                if not chunk_bytes:
                    break

                chunk_size_actual = len(
                    chunk_bytes
                )

                total_size += chunk_size_actual

                # Complete-file hash.
                complete_hash.update(
                    chunk_bytes
                )

                # Individual chunk hash.
                chunk_hash = hashlib.sha256(
                    chunk_bytes
                ).hexdigest()

                chunk_filename = (
                    f"{filename}.part{chunk_index:06d}"
                )

                telegram_message = (
                    await self.telegram.upload(
                        chat_id=channel.telegram_chat_id,
                        file_bytes=chunk_bytes,
                        filename=chunk_filename,
                    )
                )

                telegram_document = (
                    telegram_message.get(
                        "document"
                    )
                )

                if not telegram_document:
                    raise TelegramStorageError(
                        "Telegram did not return "
                        "a document for chunk."
                    )

                telegram_message_id = (
                    telegram_message["message_id"]
                )

                telegram_file_id = (
                    telegram_document["file_id"]
                )

                chunk_record = FileChunk(
                    file_id=file_record.id,

                    storage_channel_id=channel.id,

                    chunk_index=chunk_index,

                    size=chunk_size_actual,

                    sha256=chunk_hash,

                    telegram_message_id=telegram_message_id,

                    telegram_file_id=telegram_file_id,
                )


                self.chunk_repository.create(
                    chunk_record
                )

                uploaded_telegram_messages.append(
                    telegram_message_id
                )

                chunk_index += 1

            if total_size != file_size:
                raise ValueError(
                    "Uploaded file size changed "
                    "during chunked upload."
                )

            file_record.sha256 = (
                complete_hash.hexdigest()
            )

            file_record.chunk_count = (
                chunk_index
            )

            file_record.is_chunked = True

            file_record.status = "STORED"

            self.db.commit()
            self.db.refresh(file_record)

            return file_record

        except Exception:

            self.db.rollback()

            # Best-effort cleanup of Telegram
            # chunks that were already uploaded.
            for message_id in (
                uploaded_telegram_messages
            ):
                try:
                    await self.telegram.delete_message(
                        chat_id=(
                            channel.telegram_chat_id
                        ),
                        message_id=message_id,
                    )
                except Exception:
                    pass

            raise

    async def download(
        self,
        file: File,
    ) -> bytes:

        chunks = (
            self.chunk_repository.get_by_file(
                file.id
            )
        )

        if not chunks:
            raise ValueError(
                "No chunks found for file."
            )

        complete_hash = hashlib.sha256()

        file_bytes = bytearray()

        expected_index = 0

        for chunk in chunks:

            if chunk.chunk_index != expected_index:
                raise ValueError(
                    "File chunks are out of order."
                )

            chunk_bytes = (
                await self.telegram.get_file(
                    chunk.telegram_file_id
                )
            )

            actual_chunk_hash = (
                hashlib.sha256(
                    chunk_bytes
                ).hexdigest()
            )

            if (
                actual_chunk_hash
                != chunk.sha256
            ):
                raise ValueError(
                    f"Chunk {chunk.chunk_index} "
                    "failed integrity verification."
                )

            if len(chunk_bytes) != chunk.size:
                raise ValueError(
                    f"Chunk {chunk.chunk_index} "
                    "has an unexpected size."
                )

            complete_hash.update(
                chunk_bytes
            )

            file_bytes.extend(
                chunk_bytes
            )

            expected_index += 1

        final_hash = (
            complete_hash.hexdigest()
        )

        if final_hash != file.sha256:
            raise ValueError(
                "Complete file integrity "
                "verification failed."
            )

        if len(file_bytes) != file.size:
            raise ValueError(
                "Reconstructed file size "
                "does not match database."
            )

        return bytes(file_bytes)


    async def download_to_temp_file(
        self,
        file: File,
    ) -> str:

        chunks = self.chunk_repository.get_by_file(
            file.id
        )

        if not chunks:
            raise ValueError(
                "No chunks found for file."
            )

        temp_file = tempfile.NamedTemporaryFile(
            delete=False
        )

        temp_path = temp_file.name

        complete_hash = hashlib.sha256()
        expected_index = 0
        total_size = 0

        try:

            with temp_file:

                for chunk in chunks:

                    # Verify chunk order
                    if chunk.chunk_index != expected_index:
                        raise ValueError(
                            "File chunks are out of order."
                        )

                    # Download chunk
                    chunk_bytes = (
                        await self.telegram.get_file(
                            chunk.telegram_file_id
                        )
                    )

                    # Verify chunk hash
                    actual_chunk_hash = (
                        hashlib.sha256(
                            chunk_bytes
                        ).hexdigest()
                    )

                    if (
                        actual_chunk_hash
                        != chunk.sha256
                    ):
                        raise ValueError(
                            f"Chunk {chunk.chunk_index} "
                            "failed integrity verification."
                        )

                    # Verify chunk size
                    if len(chunk_bytes) != chunk.size:
                        raise ValueError(
                            f"Chunk {chunk.chunk_index} "
                            "has an unexpected size."
                        )

                    # Write verified chunk
                    temp_file.write(chunk_bytes)

                    # Update complete-file verification
                    complete_hash.update(
                        chunk_bytes
                    )

                    total_size += len(chunk_bytes)
                    expected_index += 1

            # Verify chunk count
            if expected_index != file.chunk_count:
                raise ValueError(
                    "File chunk count does not match database."
                )

            # Verify complete hash
            final_hash = complete_hash.hexdigest()

            if final_hash != file.sha256:
                raise ValueError(
                    "Complete file integrity verification failed."
                )

            # Verify complete size
            if total_size != file.size:
                raise ValueError(
                    "Reconstructed file size does not "
                    "match database."
                )

            return temp_path

        except Exception:

            try:
                os.remove(temp_path)
            except OSError:
                pass

            raise

