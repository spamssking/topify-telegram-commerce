# app/workers/upload_worker.py

import asyncio
import hashlib
import os

from datetime import (
    datetime,
    timezone,
    timedelta,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

from app.models.upload_job import UploadJob
from app.models.file import File
from app.models.user import User

from app.repositories.channel_repository import (
    ChannelRepository,
)

from app.services.channel_selector import (
    ChannelSelector,
)

from app.services.staging_storage import (
    StagingStorage,
)

from app.services.storage_router import (
    StorageRouter,
)

from app.services.telegram_errors import (
    TelegramRateLimitError,
    TelegramTemporaryError,
    TelegramPermanentError,
)


POLL_INTERVAL = 2

MAX_ATTEMPTS = 10


class UploadWorker:

    def __init__(self):

        self.staging = StagingStorage()

        self.storage = StorageRouter()

        self.channel_selector = ChannelSelector()

    # =====================================================
    # DATABASE
    # =====================================================

    def get_db(self) -> Session:

        return SessionLocal()

    # =====================================================
    # FIND JOB
    # =====================================================

    def find_job(
        self,
        db: Session,
    ):

        now = datetime.now(timezone.utc)

        job = (
            db.query(UploadJob)
            .filter(
                UploadJob.status.in_(
                    [
                        "QUEUED",
                        "RETRYING",
                    ]
                ),
                (
                    UploadJob.next_attempt_at == None
                )
                | (
                    UploadJob.next_attempt_at <= now
                ),
            )
            .order_by(
                UploadJob.created_at
            )
            .first()
        )

        if job:

            print("-" * 50)
            print("[QUEUE] Selected job")
            print(f"[QUEUE] id={job.id}")
            print(f"[QUEUE] status={job.status}")
            print(
                f"[QUEUE] filename="
                f"{job.original_filename}"
            )
            print(
                f"[QUEUE] size="
                f"{job.file_size}"
            )
            print(
                f"[QUEUE] attempts="
                f"{job.attempts}"
            )
            print(
                f"[QUEUE] max_attempts="
                f"{job.max_attempts}"
            )
            print(
                f"[QUEUE] next_attempt_at="
                f"{job.next_attempt_at}"
            )
            print(
                f"[QUEUE] created_at="
                f"{job.created_at}"
            )
            print("-" * 50)

        return job

    # =====================================================
    # PROCESS JOB
    # =====================================================

    async def process_job(
        self,
        db: Session,
        job: UploadJob,
    ):

        print(
            f"[JOB START] "
            f"id={job.id} "
            f"filename={job.original_filename} "
            f"size={job.file_size} "
            f"current_status={job.status} "
            f"attempt={job.attempts + 1}/"
            f"{job.max_attempts}"
        )

        job.status = "UPLOADING"

        job.attempts += 1

        job.next_attempt_at = None

        db.commit()

        print(
            f"[JOB STATE] "
            f"id={job.id} "
            f"status={job.status} "
            f"attempt={job.attempts}"
        )

        try:

            await self._upload(
                db,
                job,
            )

        except TelegramRateLimitError as exc:

            await self._retry_rate_limit(
                db,
                job,
                exc,
            )

        except TelegramTemporaryError as exc:

            await self._retry_temporary(
                db,
                job,
                exc,
            )

        except TelegramPermanentError as exc:

            await self._fail(
                db,
                job,
                str(exc),
            )

        except Exception as exc:

            print(
                f"[ERROR] "
                f"id={job.id} "
                f"type={type(exc).__name__} "
                f"error={exc}"
            )

            await self._retry_temporary(
                db,
                job,
                exc,
            )

    # =====================================================
    # SHA256
    # =====================================================

    def calculate_sha256(
        self,
        path: str,
    ) -> str:

        digest = hashlib.sha256()

        with open(
            path,
            "rb",
        ) as file:

            while True:

                chunk = file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(chunk)

        return digest.hexdigest()

    # =====================================================
    # EXTRACT TELEGRAM MEDIA
    # =====================================================

    def extract_telegram_media(
        self,
        telegram_message: dict,
    ):

        """
        Telegram can return uploaded media under
        different keys depending on the file type.

        Document:
            {
                "document": {
                    "file_id": "...",
                    "file_size": ...
                }
            }

        Audio:
            {
                "audio": {
                    "file_id": "...",
                    "file_size": ...
                }
            }

        Video:
            {
                "video": {
                    "file_id": "...",
                    "file_size": ...
                }
            }

        This method accepts all three.
        """

        if not isinstance(
            telegram_message,
            dict,
        ):

            raise TelegramTemporaryError(
                "Telegram returned an invalid "
                "response type."
            )

        # -------------------------------------------------
        # DOCUMENT
        # -------------------------------------------------

        document = telegram_message.get(
            "document"
        )

        if document:

            return (
                "document",
                document,
            )

        # -------------------------------------------------
        # AUDIO
        # -------------------------------------------------

        audio = telegram_message.get(
            "audio"
        )

        if audio:

            return (
                "audio",
                audio,
            )

        # -------------------------------------------------
        # VIDEO
        # -------------------------------------------------

        video = telegram_message.get(
            "video"
        )

        if video:

            return (
                "video",
                video,
            )

        # -------------------------------------------------
        # NOTHING FOUND
        # -------------------------------------------------

        print(
            "[TELEGRAM MEDIA ERROR] "
            "No supported media field found."
        )

        print(
            f"[TELEGRAM MEDIA ERROR] "
            f"response_keys="
            f"{list(telegram_message.keys())}"
        )

        print(
            f"[TELEGRAM MEDIA ERROR] "
            f"response="
            f"{telegram_message}"
        )

        raise TelegramTemporaryError(
            "Telegram returned a message without "
            "document, audio, or video."
        )

    # =====================================================
    # UPLOAD
    # =====================================================

    async def _upload(
        self,
        db: Session,
        job: UploadJob,
    ):

        print(
            f"[UPLOAD START] job={job.id}"
        )

        # -------------------------------------------------
        # STAGING FILE
        # -------------------------------------------------

        if not os.path.exists(
            job.staging_path
        ):

            raise TelegramPermanentError(
                "Staged upload file no longer exists."
            )

        actual_size = os.path.getsize(
            job.staging_path
        )

        print(
            f"[STAGING] path="
            f"{job.staging_path}"
        )

        print(
            f"[STAGING] expected_size="
            f"{job.file_size} "
            f"actual_size="
            f"{actual_size}"
        )

        if actual_size != job.file_size:

            raise TelegramPermanentError(
                "Staged file size does not "
                "match upload job size."
            )

        # -------------------------------------------------
        # LOAD USER
        # -------------------------------------------------

        user = db.get(
            User,
            job.user_id,
        )

        if not user:

            raise TelegramPermanentError(
                "Upload owner no longer exists."
            )

        print(
            f"[USER] user_id={user.id}"
        )

        # -------------------------------------------------
        # LOAD PLAN
        # -------------------------------------------------

        plan = user.plan

        if not plan:

            raise TelegramPermanentError(
                "User does not have an active plan."
            )

        print(
            f"[PLAN] max_file_size="
            f"{plan.max_file_size_bytes}"
        )

        print(
            f"[PLAN] storage_quota="
            f"{plan.storage_quota_bytes}"
        )

        # -------------------------------------------------
        # FILE SIZE CHECK
        # -------------------------------------------------

        if (
            job.file_size
            > plan.max_file_size_bytes
        ):

            raise TelegramPermanentError(
                "File exceeds the maximum "
                "file size for the user's plan."
            )

        # -------------------------------------------------
        # STORAGE QUOTA CHECK
        # -------------------------------------------------

        locked_user = (
            db.execute(
                select(User)
                .where(
                    User.id == job.user_id
                )
                .with_for_update()
            )
            .scalar_one()
        )

        print(
            f"[QUOTA] "
            f"storage_used="
            f"{locked_user.storage_used} "
            f"file_size="
            f"{job.file_size} "
            f"quota="
            f"{plan.storage_quota_bytes}"
        )

        if (
            locked_user.storage_used
            + job.file_size
            > plan.storage_quota_bytes
        ):

            raise TelegramPermanentError(
                "Storage quota exceeded."
            )

        db.commit()

        # -------------------------------------------------
        # STORAGE CHANNELS
        # -------------------------------------------------

        channels = (
            ChannelRepository(
                db
            ).get_active()
        )

        print(
            f"[CHANNELS] "
            f"active_count={len(channels)}"
        )

        if not channels:

            raise TelegramPermanentError(
                "No active Telegram storage "
                "channels are available."
            )

        for index, item in enumerate(
            channels,
            start=1,
        ):

            print(
                f"[CHANNEL] {index}: "
                f"id={item.id} "
                f"telegram_chat_id="
                f"{item.telegram_chat_id}"
            )

        channel = (
            self.channel_selector.select(
                channels
            )
        )

        print(
            f"[CHANNEL SELECTED] "
            f"database_id={channel.id} "
            f"telegram_chat_id="
            f"{channel.telegram_chat_id}"
        )

        # -------------------------------------------------
        # PRIMARY STORAGE
        # -------------------------------------------------

        backend = self.storage.primary()

        print(
            f"[BACKEND] "
            f"primary={type(backend).__name__}"
        )

        print(
            f"[UPLOAD REQUEST] "
            f"job={job.id} "
            f"backend=LOCAL_BOT "
            f"chat_id={channel.telegram_chat_id} "
            f"filename={job.original_filename} "
            f"size={job.file_size}"
        )

        try:

            telegram_message = (
                await backend.upload(
                    chat_id=(
                        channel.telegram_chat_id
                    ),
                    file_path=(
                        job.staging_path
                    ),
                    filename=(
                        job.original_filename
                    ),
                )
            )

            storage_backend = "LOCAL_BOT"

        except (
            TelegramRateLimitError,
            TelegramTemporaryError,
        ):

            raise

        except TelegramPermanentError:

            print(
                "[BACKEND] "
                "Primary backend permanently failed. "
                "Trying fallback."
            )

            cloud = self.storage.fallback()

            print(
                f"[UPLOAD REQUEST] "
                f"job={job.id} "
                f"backend=CLOUD_BOT "
                f"chat_id={channel.telegram_chat_id} "
                f"filename={job.original_filename} "
                f"size={job.file_size}"
            )

            telegram_message = (
                await cloud.upload(
                    chat_id=(
                        channel.telegram_chat_id
                    ),
                    file_path=(
                        job.staging_path
                    ),
                    filename=(
                        job.original_filename
                    ),
                )
            )

            storage_backend = "CLOUD_BOT"

        # -------------------------------------------------
        # TELEGRAM RESPONSE
        # -------------------------------------------------

        print("=" * 50)

        print(
            "[TELEGRAM RESPONSE]"
        )

        print(
            f"job_id={job.id}"
        )

        print(
            f"backend={storage_backend}"
        )

        print(
            f"response_type="
            f"{type(telegram_message).__name__}"
        )

        print(
            f"response={telegram_message}"
        )

        if isinstance(
            telegram_message,
            dict,
        ):

            print(
                f"response_keys="
                f"{list(telegram_message.keys())}"
            )

            print(
                f"message_id="
                f"{telegram_message.get('message_id')}"
            )

        print("=" * 50)

        # -------------------------------------------------
        # EXTRACT MEDIA
        # -------------------------------------------------

        media_type, media = (
            self.extract_telegram_media(
                telegram_message
            )
        )

        print(
            f"[MEDIA SUCCESS] "
            f"job={job.id}"
        )

        print(
            f"[MEDIA TYPE] "
            f"{media_type}"
        )

        print(
            f"[MEDIA FILE ID] "
            f"{media.get('file_id')}"
        )

        print(
            f"[MEDIA FILE UNIQUE ID] "
            f"{media.get('file_unique_id')}"
        )

        print(
            f"[MEDIA FILE SIZE] "
            f"{media.get('file_size')}"
        )

        # -------------------------------------------------
        # VERIFY FILE ID
        # -------------------------------------------------

        telegram_file_id = media.get(
            "file_id"
        )

        if not telegram_file_id:

            raise TelegramTemporaryError(
                f"Telegram returned a {media_type} "
                "without a file_id."
            )

        # -------------------------------------------------
        # VERIFY MESSAGE ID
        # -------------------------------------------------

        telegram_message_id = (
            telegram_message.get(
                "message_id"
            )
        )

        if not telegram_message_id:

            raise TelegramTemporaryError(
                "Telegram returned media but "
                "no message_id."
            )

        # -------------------------------------------------
        # HASH
        # -------------------------------------------------

        sha256 = (
            self.calculate_sha256(
                job.staging_path
            )
        )

        print(
            f"[HASH] sha256={sha256}"
        )

        # -------------------------------------------------
        # FINAL QUOTA CHECK
        # -------------------------------------------------

        locked_user = (
            db.execute(
                select(User)
                .where(
                    User.id == job.user_id
                )
                .with_for_update()
            )
            .scalar_one()
        )

        if (
            locked_user.storage_used
            + job.file_size
            > plan.storage_quota_bytes
        ):

            db.rollback()

            raise TelegramPermanentError(
                "Storage quota was exceeded "
                "before the upload could be committed."
            )

        # -------------------------------------------------
        # CREATE FILE RECORD
        # -------------------------------------------------

        file_record = File(
            user_id=job.user_id,

            storage_channel_id=channel.id,

            telegram_message_id=(
                telegram_message_id
            ),

            telegram_file_id=(
                telegram_file_id
            ),

            name=job.original_filename,

            mime_type=job.mime_type,

            size=job.file_size,

            sha256=sha256,

            status="STORED",

            is_chunked=False,

            chunk_count=1,
        )

        db.add(
            file_record
        )

        db.flush()

        # -------------------------------------------------
        # UPDATE QUOTA
        # -------------------------------------------------

        locked_user.storage_used += (
            job.file_size
        )

        # -------------------------------------------------
        # COMPLETE JOB
        # -------------------------------------------------

        job.file_id = file_record.id

        job.status = "COMPLETED"

        job.completed_at = (
            datetime.now(
                timezone.utc
            )
        )

        job.last_error = None

        job.next_attempt_at = None

        job.storage_backend = (
            storage_backend
        )

        # -------------------------------------------------
        # COMMIT
        # -------------------------------------------------

        db.commit()

        # -------------------------------------------------
        # DELETE STAGING FILE
        # -------------------------------------------------

        self.staging.delete(
            job.staging_path
        )

        print(
            f"[UPLOAD COMPLETED] "
            f"job={job.id}"
        )

        print(
            f"[UPLOAD COMPLETED] "
            f"media_type={media_type}"
        )

        print(
            f"[UPLOAD COMPLETED] "
            f"telegram_message_id="
            f"{telegram_message_id}"
        )

        print(
            f"[UPLOAD COMPLETED] "
            f"telegram_file_id="
            f"{telegram_file_id}"
        )

        print(
            f"[UPLOAD COMPLETED] "
            f"file_record_id="
            f"{file_record.id}"
        )

    # =====================================================
    # RATE LIMIT RETRY
    # =====================================================

    async def _retry_rate_limit(
        self,
        db: Session,
        job: UploadJob,
        exc: TelegramRateLimitError,
    ):

        if (
            job.attempts
            >= job.max_attempts
        ):

            await self._fail(
                db,
                job,
                str(exc),
            )

            return

        job.status = "RETRYING"

        job.next_attempt_at = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                seconds=exc.retry_after
            )
        )

        job.last_error = str(exc)

        db.commit()

        print(
            f"Telegram rate limit for "
            f"job {job.id}. "
            f"Retrying in "
            f"{exc.retry_after} seconds."
        )

    # =====================================================
    # TEMPORARY RETRY
    # =====================================================

    async def _retry_temporary(
        self,
        db: Session,
        job: UploadJob,
        exc: Exception,
    ):

        if (
            job.attempts
            >= job.max_attempts
        ):

            await self._fail(
                db,
                job,
                str(exc),
            )

            return

        delay = min(
            300,
            2 ** job.attempts,
        )

        job.status = "RETRYING"

        job.next_attempt_at = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                seconds=delay
            )
        )

        job.last_error = str(exc)

        db.commit()

        print(
            f"Temporary upload failure "
            f"for job {job.id}. "
            f"error_type="
            f"{type(exc).__name__} "
            f"error={exc} "
            f"retrying in {delay} seconds."
        )

    # =====================================================
    # FAIL
    # =====================================================

    async def _fail(
        self,
        db: Session,
        job: UploadJob,
        error: str,
    ):

        job.status = "FAILED"

        job.last_error = error

        job.next_attempt_at = None

        db.commit()

        print(
            f"Upload job {job.id} failed: "
            f"{error}"
        )

    # =====================================================
    # RUN
    # =====================================================

    async def run(self):

        print(
            "================================"
        )

        print(
            "Telegram Cloud Storage Worker"
        )

        print(
            "Upload worker started."
        )

        print(
            "Primary backend: LOCAL_BOT"
        )

        print(
            "Fallback backend: CLOUD_BOT"
        )

        print(
            "================================"
        )

        while True:

            db = self.get_db()

            try:

                job = self.find_job(
                    db
                )

                if job:

                    print(
                        f"Processing upload "
                        f"job {job.id}"
                    )

                    await self.process_job(
                        db,
                        job,
                    )

                else:

                    await asyncio.sleep(
                        POLL_INTERVAL
                    )

            except Exception as exc:

                print(
                    "WORKER LOOP ERROR: "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                await asyncio.sleep(
                    POLL_INTERVAL
                )

            finally:

                db.close()


if __name__ == "__main__":

    worker = UploadWorker()

    asyncio.run(
        worker.run()
    )
