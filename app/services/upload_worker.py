import asyncio

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import SessionLocal

from app.models.upload_job import UploadJob
from app.models.user import User

from app.services.local_telegram_storage import (
    LocalTelegramStorage,
)

from app.services.telegram_storage import (
    TelegramStorage,
)

from app.services.staging_storage import (
    StagingStorage,
)

from app.repositories.channel_repository import (
    ChannelRepository,
)

from app.services.channel_selector import (
    ChannelSelector,
)


class UploadWorker:

    def __init__(self):

        self.staging = StagingStorage()

        self.cloud = TelegramStorage()

        self.local = LocalTelegramStorage()

        self.channel_selector = (
            ChannelSelector()
        )

    async def process_job(
        self,
        job: UploadJob,
    ):

        db = SessionLocal()

        try:

            job.status = "PROCESSING"

            job.attempts += 1

            job.started_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

            user = db.get(
                User,
                job.user_id,
            )

            if not user:
                raise RuntimeError(
                    "User no longer exists."
                )

            channels = (
                ChannelRepository(db)
                .get_active()
            )

            if not channels:
                raise RuntimeError(
                    "No storage channels available."
                )

            channel = (
                self.channel_selector
                .select(channels)
            )

            path = (
                self.staging
                .create_path(job.id)
            )

            if not path.exists():
                raise RuntimeError(
                    "Staged upload file does not exist."
                )

            if job.backend == "local":

                result = (
                    await self.local
                    .upload_file(
                        chat_id=(
                            channel.telegram_chat_id
                        ),
                        file_path=path,
                        filename=job.filename,
                    )
                )

            else:

                with open(
                    path,
                    "rb",
                ) as file:

                    file_bytes = file.read()

                result = (
                    await self.cloud.upload(
                        chat_id=(
                            channel.telegram_chat_id
                        ),
                        file_bytes=file_bytes,
                        filename=job.filename,
                    )
                )

            job.status = "STORED"

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            db.commit()

            return result

        except Exception as exc:

            job.status = "RETRYING"

            job.last_error = str(exc)

            db.commit()

            raise

        finally:

            db.close()
