import hashlib
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File
from app.models.user import User

from app.repositories.channel_repository import ChannelRepository
from app.repositories.file_repository import FileRepository
from app.repositories.file_chunk_repository import FileChunkRepository

from app.services.channel_selector import ChannelSelector
from app.services.chunked_file_service import ChunkedFileService
from app.services.telegram_storage import TelegramStorage


class FileService:

    def __init__(self, db: Session):
        self.db = db

        # -------------------------------------------------
        # REPOSITORIES
        # -------------------------------------------------

        self.file_repository = FileRepository(db)

        self.chunk_repository = FileChunkRepository(db)

        self.channel_repository = ChannelRepository(db)

        # -------------------------------------------------
        # SERVICES
        # -------------------------------------------------

        self.channel_selector = ChannelSelector()

        self.telegram = TelegramStorage()

        # Chunking is isolated in its own service.
        # It is only called when a PRO user uploads a file
        # larger than the configured Telegram chunk size.
        self.chunked_file_service = ChunkedFileService(db)

    # =====================================================
    # UPLOAD
    # =====================================================

    async def upload(
        self,
        upload: UploadFile,
        user_id: str,
    ) -> File:

        # -------------------------------------------------
        # LOAD USER
        # -------------------------------------------------

        user = self.db.get(
            User,
            user_id,
        )

        if not user:
            raise ValueError(
                "User account not found."
            )

        if not user.is_active:
            raise ValueError(
                "Account is disabled."
            )

        if not user.is_verified:
            raise ValueError(
                "Email address is not verified."
            )

        # -------------------------------------------------
        # LOAD USER PLAN
        # -------------------------------------------------

        plan = user.plan

        if not plan:
            raise ValueError(
                "User does not have an active plan."
            )

        # -------------------------------------------------
        # DETERMINE FILE SIZE
        # -------------------------------------------------

        file_size = await self._get_upload_size(
            upload
        )

        if file_size <= 0:
            raise ValueError(
                "Uploaded file is empty."
            )

        # -------------------------------------------------
        # PLAN FILE SIZE LIMIT
        # -------------------------------------------------

        if (
            file_size
            > plan.max_file_size_bytes
        ):
            max_mb = (
                plan.max_file_size_bytes
                / 1024
                / 1024
            )

            raise ValueError(
                f"File is too large for your "
                f"{plan.name} plan. "
                f"Maximum file size is "
                f"{max_mb:.2f} MB."
            )

        # -------------------------------------------------
        # STORAGE QUOTA
        # -------------------------------------------------

        if (
            user.storage_used + file_size
            > plan.storage_quota_bytes
        ):
            raise ValueError(
                "Storage quota exceeded."
            )

        # -------------------------------------------------
        # DETERMINE WHETHER USER IS PRO
        # -------------------------------------------------

        is_pro = (
            plan.code.upper() == "PRO"
        )

        # -------------------------------------------------
        # PRO CHUNKING
        # -------------------------------------------------
        #
        # A Pro user gets the chunking system ONLY when
        # the uploaded file is larger than the configured
        # Telegram chunk size.
        #
        # Example:
        #
        # 40 MB  -> normal Telegram upload
        # 49 MB  -> normal Telegram upload
        # 100 MB -> chunked upload
        # 2 GB   -> chunked upload
        #
        # The chunk size is deliberately kept below the
        # Telegram Bot API limit.
        # -------------------------------------------------

        if (
            is_pro
            and file_size
            > settings.telegram_chunk_size
        ):

            return await (
                self.chunked_file_service.upload(
                    upload=upload,
                    user=user,
                    file_size=file_size,
                    chunk_size=(
                        settings.telegram_chunk_size
                    ),
                )
            )

        # -------------------------------------------------
        # NORMAL SINGLE-FILE UPLOAD
        # -------------------------------------------------

        return await self._upload_single_file(
            upload=upload,
            user=user,
            file_size=file_size,
        )

    # =====================================================
    # GET UPLOAD SIZE
    # =====================================================

    async def _get_upload_size(
        self,
        upload: UploadFile,
    ) -> int:

        file_object = upload.file

        # Move to the end of the temporary file.
        file_object.seek(0, 2)

        size = file_object.tell()

        # IMPORTANT:
        #
        # Reset the file position so the actual upload
        # starts from byte zero.
        #
        file_object.seek(0)

        return size

    # =====================================================
    # SINGLE FILE UPLOAD
    # =====================================================

    async def _upload_single_file(
        self,
        upload: UploadFile,
        user: User,
        file_size: int,
    ) -> File:

        # -------------------------------------------------
        # READ FILE
        # -------------------------------------------------

        file_bytes = await upload.read()

        if not file_bytes:
            raise ValueError(
                "Uploaded file is empty."
            )

        # -------------------------------------------------
        # VERIFY SIZE
        # -------------------------------------------------

        actual_size = len(file_bytes)

        if actual_size != file_size:
            raise ValueError(
                "Uploaded file size changed "
                "while processing."
            )

        # -------------------------------------------------
        # HASH
        # -------------------------------------------------

        sha256 = hashlib.sha256(
            file_bytes
        ).hexdigest()

        # -------------------------------------------------
        # SELECT STORAGE CHANNEL
        # -------------------------------------------------

        channels = (
            self.channel_repository
            .get_active()
        )

        if not channels:

            raise ValueError(
                "No active Telegram storage "
                "channel is available."
            )

        channel = self.channel_selector.select(
            channels
        )

        # -------------------------------------------------
        # UPLOAD TO TELEGRAM
        # -------------------------------------------------

        telegram_message = (
            await self.telegram.upload(
                chat_id=channel.telegram_chat_id,
                file_bytes=file_bytes,
                filename=(
                    upload.filename
                    or "file"
                ),
            )
        )

        # -------------------------------------------------
        # EXTRACT FILE INFORMATION
        # -------------------------------------------------
        #
        # Telegram may return the uploaded file as:
        #
        #   document
        #   audio
        #   video
        #   animation
        #   photo
        #
        # Do NOT assume that every upload comes back
        # inside telegram_message["document"].
        #

        file_info = (
            self.telegram.extract_file_info(
                telegram_message
            )
        )

        telegram_file_id = (
            file_info.get("file_id")
        )

        if not telegram_file_id:

            raise RuntimeError(
                "Telegram did not return a file ID."
            )

        # -------------------------------------------------
        # CREATE DATABASE RECORD
        # -------------------------------------------------

        file_record = File(
            user_id=user.id,

            storage_channel_id=channel.id,

            telegram_message_id=(
                telegram_message[
                    "message_id"
                ]
            ),

            telegram_file_id=(
                telegram_file_id
            ),

            storage_backend="LOCAL_BOT",

            name=(
                upload.filename
                or "file"
            ),

            mime_type=(
                upload.content_type
            ),

            size=file_size,

            sha256=sha256,

            status="STORED",

            is_chunked=False,

            chunk_count=1,
        )

        # -------------------------------------------------
        # SAVE FILE
        # -------------------------------------------------

        file_record = (
            self.file_repository.create(
                file_record
            )
        )

        # -------------------------------------------------
        # UPDATE STORAGE USAGE
        # -------------------------------------------------

        user.storage_used += file_size

        self.db.commit()

        self.db.refresh(user)

        return file_record


    # =====================================================
    # DOWNLOAD
    # =====================================================

    async def download(
        self,
        file_id: str,
        user_id: str,
    ) -> tuple[File, bytes]:

        # -------------------------------------------------
        # FIND FILE
        # -------------------------------------------------

        file = (
            self.file_repository
            .get_user_file(
                file_id=file_id,
                user_id=user_id,
            )
        )

        if not file:
            raise FileNotFoundError(
                "File not found."
            )

        # -------------------------------------------------
        # CHUNKED FILE
        # -------------------------------------------------

        if file.is_chunked:

            file_bytes = (
                await self.chunked_file_service
                .download(file)
            )

        # -------------------------------------------------
        # NORMAL FILE
        # -------------------------------------------------

        else:

            if not file.telegram_file_id:
                raise RuntimeError(
                    "File does not have a "
                    "Telegram file ID."
                )

            file_bytes = (
                await self.telegram.get_file(
                    file.telegram_file_id
                )
            )

        # -------------------------------------------------
        # VERIFY COMPLETE FILE HASH
        # -------------------------------------------------

        calculated_hash = (
            hashlib.sha256(
                file_bytes
            ).hexdigest()
        )

        if calculated_hash != file.sha256:
            raise RuntimeError(
                "Downloaded file integrity "
                "check failed."
            )

        # -------------------------------------------------
        # VERIFY COMPLETE FILE SIZE
        # -------------------------------------------------

        if len(file_bytes) != file.size:
            raise RuntimeError(
                "Downloaded file size does not "
                "match the stored file."
            )

        return file, file_bytes

    # =====================================================
    # DELETE
    # =====================================================

    async def delete(
        self,
        file_id: str,
        user_id: str,
    ) -> None:

        # -------------------------------------------------
        # FIND FILE
        # -------------------------------------------------

        file = (
            self.file_repository
            .get_user_file(
                file_id=file_id,
                user_id=user_id,
            )
        )

        if not file:
            raise FileNotFoundError(
                "File not found."
            )

        # -------------------------------------------------
        # CHUNKED FILE
        # -------------------------------------------------

        if file.is_chunked:

            chunks = (
                self.chunk_repository
                .get_by_file(
                    file.id
                )
            )

            # Each chunk may potentially be stored
            # in a different Telegram channel.
            #
            # Therefore we use the channel recorded
            # on each chunk rather than assuming that
            # every chunk belongs to the parent file's
            # channel.

            for chunk in chunks:

                channel = (
                    self.channel_repository
                    .get_by_id(
                        chunk.storage_channel_id
                    )
                )

                if not channel:
                    raise RuntimeError(
                        "Storage channel for "
                        "file chunk no longer exists."
                    )

                await self.telegram.delete_message(
                    chat_id=(
                        channel.telegram_chat_id
                    ),
                    message_id=(
                        chunk.telegram_message_id
                    ),
                )

        # -------------------------------------------------
        # NORMAL FILE
        # -------------------------------------------------

        else:

            channel = (
                self.channel_repository
                .get_by_id(
                    file.storage_channel_id
                )
            )

            if not channel:
                raise RuntimeError(
                    "Storage channel no longer exists."
                )

            if not file.telegram_message_id:
                raise RuntimeError(
                    "File does not have a "
                    "Telegram message ID."
                )

            await self.telegram.delete_message(
                chat_id=(
                    channel.telegram_chat_id
                ),
                message_id=(
                    file.telegram_message_id
                ),
            )

        # -------------------------------------------------
        # MARK FILE DELETED
        # -------------------------------------------------

        file.deleted_at = (
            datetime.now(timezone.utc)
        )

        file.status = "DELETED"

        # -------------------------------------------------
        # RETURN STORAGE QUOTA
        # -------------------------------------------------

        user = self.db.get(
            User,
            user_id,
        )

        if user:

            user.storage_used = max(
                0,
                user.storage_used - file.size,
            )

        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        self.db.commit()


    def list_files(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        status: str | None = None,
        sort: str = "created_at",
    ) -> dict:

        files, total = (
            self.file_repository.get_user_files(
                user_id=user_id,
                page=max(page, 1),
                page_size=min(max(page_size, 1), 100),
                search=search,
                status=status,
                sort=sort,
            )
        )

        return {
            "items": files,
            "page": page,
            "page_size": page_size,
            "total": total,
        }
