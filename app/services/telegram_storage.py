# app/services/telegram_storage.py

from pathlib import Path

import httpx

from app.core.config import settings

from app.services.telegram_errors import (
    TelegramRateLimitError,
    TelegramStorageError,
    TelegramTemporaryError,
    TelegramPermanentError,
)


class TelegramStorage:

    def __init__(self):

        self.base_url = (
            "https://api.telegram.org/bot"
            f"{settings.telegram_cloud_bot_token}"
        )

        if not settings.telegram_cloud_bot_token:
            raise RuntimeError(
                "TELEGRAM_CLOUD_BOT_TOKEN "
                "is not configured."
            )

    # =====================================================
    # UPLOAD
    # =====================================================

    async def upload(
        self,
        chat_id: int,
        file_path: str | None = None,
        filename: str = "file",
        file_bytes: bytes | None = None,
    ) -> dict:

        # -------------------------------------------------
        # VALIDATE INPUT
        # -------------------------------------------------

        if file_path is None and file_bytes is None:
            raise ValueError(
                "Either file_path or file_bytes must be provided."
            )

        if file_path is not None:
            path = Path(file_path)

            if not path.exists():
                raise TelegramPermanentError(
                    "Staged file does not exist."
                )

        # -------------------------------------------------
        # TELEGRAM ENDPOINT
        # -------------------------------------------------

        url = (
            f"{self.base_url}/sendDocument"
        )

        # -------------------------------------------------
        # TIMEOUT
        # -------------------------------------------------

        timeout = httpx.Timeout(
            connect=30.0,
            read=1800.0,
            write=1800.0,
            pool=60.0,
        )

        try:

            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:

                # -----------------------------------------
                # FILE PATH UPLOAD
                # -----------------------------------------

                if file_path is not None:

                    with path.open("rb") as file:

                        response = await client.post(
                            url,
                            data={
                                "chat_id": str(chat_id),
                            },
                            files={
                                "document": (
                                    filename,
                                    file,
                                )
                            },
                        )

                # -----------------------------------------
                # BYTES UPLOAD
                # -----------------------------------------

                else:

                    response = await client.post(
                        url,
                        data={
                            "chat_id": str(chat_id),
                        },
                        files={
                            "document": (
                                filename,
                                file_bytes,
                            )
                        },
                    )

        except httpx.TimeoutException as exc:

            raise TelegramTemporaryError(
                f"Telegram upload timed out: {exc}"
            )

        except httpx.RequestError as exc:

            raise TelegramTemporaryError(
                f"Telegram connection failed: {exc}"
            )

        return self._handle_response(response)

    # =====================================================
    # DELETE MESSAGE
    # =====================================================

    async def delete_message(
        self,
        chat_id: int,
        message_id: int,
    ) -> bool:

        url = (
            f"{self.base_url}/deleteMessage"
        )

        timeout = httpx.Timeout(
            connect=30.0,
            read=60.0,
            write=60.0,
            pool=30.0,
        )

        try:

            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:

                response = await client.post(
                    url,
                    data={
                        "chat_id": str(chat_id),
                        "message_id": str(message_id),
                    },
                )

        except httpx.TimeoutException as exc:

            raise TelegramTemporaryError(
                f"Telegram delete timed out: {exc}"
            )

        except httpx.RequestError as exc:

            raise TelegramTemporaryError(
                f"Telegram delete connection failed: {exc}"
            )

        result = self._handle_response(
            response
        )

        # Telegram returns:
        #
        # {
        #     "ok": true,
        #     "result": true
        # }

        return bool(result)

    # =====================================================
    # GET FILE
    # =====================================================

    async def get_file(
        self,
        file_id: str,
    ) -> bytes:

        # -------------------------------------------------
        # STEP 1:
        # Ask Telegram for file path
        # -------------------------------------------------

        url = (
            f"{self.base_url}/getFile"
        )

        timeout = httpx.Timeout(
            connect=30.0,
            read=120.0,
            write=120.0,
            pool=30.0,
        )

        try:

            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:

                response = await client.post(
                    url,
                    data={
                        "file_id": file_id,
                    },
                )

        except httpx.TimeoutException as exc:

            raise TelegramTemporaryError(
                f"Telegram getFile timed out: {exc}"
            )

        except httpx.RequestError as exc:

            raise TelegramTemporaryError(
                f"Telegram getFile connection failed: {exc}"
            )

        result = self._handle_response(
            response
        )

        file_path = result.get(
            "file_path"
        )

        if not file_path:

            raise TelegramTemporaryError(
                "Telegram did not return a file path."
            )

        # -------------------------------------------------
        # STEP 2:
        # Download file
        # -------------------------------------------------

        download_url = (
            "https://api.telegram.org/file/bot"
            f"{settings.telegram_cloud_bot_token}"
            f"/{file_path}"
        )

        try:

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=1800.0,
                    write=1800.0,
                    pool=60.0,
                )
            ) as client:

                download_response = (
                    await client.get(
                        download_url
                    )
                )

        except httpx.TimeoutException as exc:

            raise TelegramTemporaryError(
                f"Telegram file download timed out: {exc}"
            )

        except httpx.RequestError as exc:

            raise TelegramTemporaryError(
                f"Telegram file download failed: {exc}"
            )

        if download_response.status_code != 200:

            raise TelegramTemporaryError(
                "Telegram file download failed: "
                f"{download_response.status_code}"
            )

        return download_response.content

    # =====================================================
    # EXTRACT TELEGRAM FILE
    # =====================================================

    @staticmethod
    def extract_file_info(
        telegram_message: dict,
    ) -> dict:

        # -------------------------------------------------
        # Telegram can return uploaded files as:
        #
        # document
        # audio
        # video
        # animation
        # photo
        #
        # We check all supported file-bearing fields.
        # -------------------------------------------------

        for field in (
            "document",
            "audio",
            "video",
            "animation",
        ):

            telegram_file = (
                telegram_message.get(field)
            )

            if telegram_file:

                return {
                    "type": field,
                    "file_id": telegram_file.get(
                        "file_id"
                    ),
                    "file_unique_id": telegram_file.get(
                        "file_unique_id"
                    ),
                    "file_size": telegram_file.get(
                        "file_size"
                    ),
                }

        # -------------------------------------------------
        # PHOTO
        #
        # Telegram returns photos as an array.
        # Select the largest photo.
        # -------------------------------------------------

        photos = telegram_message.get(
            "photo"
        )

        if photos:

            largest_photo = max(
                photos,
                key=lambda photo: (
                    photo.get("file_size", 0)
                ),
            )

            return {
                "type": "photo",
                "file_id": largest_photo.get(
                    "file_id"
                ),
                "file_unique_id": largest_photo.get(
                    "file_unique_id"
                ),
                "file_size": largest_photo.get(
                    "file_size"
                ),
            }

        # -------------------------------------------------
        # NOTHING FOUND
        # -------------------------------------------------

        return {}

    # =====================================================
    # RESPONSE
    # =====================================================

    def _handle_response(
        self,
        response: httpx.Response,
    ) -> dict:

        try:

            result = response.json()

        except ValueError:

            raise TelegramTemporaryError(
                "Telegram returned invalid JSON."
            )

        # -------------------------------------------------
        # RATE LIMIT
        # -------------------------------------------------

        if response.status_code == 429:

            retry_after = (
                result
                .get("parameters", {})
                .get("retry_after")
            )

            if retry_after is None:
                retry_after = 30

            raise TelegramRateLimitError(
                retry_after=int(
                    retry_after
                )
            )

        # -------------------------------------------------
        # SERVER ERROR
        # -------------------------------------------------

        if response.status_code >= 500:

            raise TelegramTemporaryError(
                "Telegram server error: "
                f"{response.status_code}"
            )

        # -------------------------------------------------
        # HTTP ERROR
        # -------------------------------------------------

        if response.status_code != 200:

            raise TelegramPermanentError(
                result.get(
                    "description",
                    "Telegram request failed.",
                )
            )

        # -------------------------------------------------
        # TELEGRAM API ERROR
        # -------------------------------------------------

        if not result.get("ok"):

            raise TelegramPermanentError(
                result.get(
                    "description",
                    "Telegram request failed.",
                )
            )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        telegram_result = result.get(
            "result"
        )

        if telegram_result is None:

            raise TelegramTemporaryError(
                "Telegram returned no result."
            )

        return telegram_result