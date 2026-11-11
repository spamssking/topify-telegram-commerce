# app/services/local_telegram_storage.py

from pathlib import Path

import httpx

from app.core.config import settings
from app.services.telegram_errors import (
    TelegramRateLimitError,
    TelegramStorageError,
    TelegramTemporaryError,
    TelegramPermanentError,
)


class LocalTelegramStorage:
    """
    Storage backend using Telegram's Local Bot API Server.

    This backend is intended to be the PRIMARY storage backend.

    Example:

        Local Bot API Server
                |
                v
        http://127.0.0.1:8081
                |
                v
            Telegram

    The local Bot API server supports large uploads and
    unlimited downloads according to Telegram's documentation.
    """

    def __init__(self):

        self.base_url = (
            settings.telegram_local_api_url
        ).rstrip("/")

        self.bot_token = (
            settings.telegram_local_bot_token
        )

        if not self.bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is not configured."
            )

    # =====================================================
    # URL
    # =====================================================

    def _url(
        self,
        method: str,
    ) -> str:

        return (
            f"{self.base_url}"
            f"/bot{self.bot_token}"
            f"/{method}"
        )

    # =====================================================
    # RESPONSE HANDLING
    # =====================================================

    def _handle_response(
        self,
        response: httpx.Response,
    ) -> dict:

        try:
            result = response.json()

        except ValueError:

            raise TelegramTemporaryError(
                "Local Bot API returned invalid JSON."
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
                "Local Bot API server error: "
                f"{response.status_code}"
            )

        # -------------------------------------------------
        # OTHER HTTP ERROR
        # -------------------------------------------------

        if response.status_code != 200:

            raise TelegramPermanentError(
                result.get(
                    "description",
                    (
                        "Local Bot API request "
                        "failed."
                    ),
                )
            )

        # -------------------------------------------------
        # TELEGRAM ERROR
        # -------------------------------------------------

        if not result.get("ok"):

            raise TelegramPermanentError(
                result.get(
                    "description",
                    (
                        "Local Telegram "
                        "operation failed."
                    ),
                )
            )

        return result["result"]

    # =====================================================
    # UPLOAD
    # =====================================================

    async def upload(
        self,
        chat_id: int,
        file_path: str,
        filename: str,
    ) -> dict:

        path = Path(file_path)

        if not path.exists():

            raise FileNotFoundError(
                f"Staged file does not exist: "
                f"{file_path}"
            )

        if not path.is_file():

            raise ValueError(
                f"Staging path is not a file: "
                f"{file_path}"
            )

        url = self._url(
            "sendDocument"
        )

        timeout = httpx.Timeout(
            connect=30.0,
            read=1800.0,
            write=1800.0,
            pool=30.0,
        )

        async with httpx.AsyncClient(
            timeout=timeout
        ) as client:

            try:

                with path.open(
                    "rb"
                ) as file:

                    response = await client.post(
                        url,
                        data={
                            "chat_id": str(
                                chat_id
                            ),
                        },
                        files={
                            "document": (
                                filename,
                                file,
                            )
                        },
                    )

            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.RemoteProtocolError,
            ) as exc:

                raise TelegramTemporaryError(
                    f"Local Bot API connection "
                    f"failed: {exc}"
                ) from exc

        return self._handle_response(
            response
        )

    # =====================================================
    # SEND TEST MESSAGE
    # =====================================================

    async def send_test_message(
        self,
        chat_id: int,
        text: str,
    ) -> dict:

        url = self._url(
            "sendMessage"
        )

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                url,
                data={
                    "chat_id": str(
                        chat_id
                    ),
                    "text": text,
                },
            )

        return self._handle_response(
            response
        )

    # =====================================================
    # GET TELEGRAM FILE INFORMATION
    # =====================================================

    async def _get_file_info(
        self,
        file_id: str,
    ) -> dict:

        url = self._url(
            "getFile"
        )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=30.0,
                read=300.0,
                write=300.0,
                pool=30.0,
            )
        ) as client:

            response = await client.get(
                url,
                params={
                    "file_id": file_id,
                },
            )

        return self._handle_response(
            response
        )

    # =====================================================
    # DOWNLOAD
    # =====================================================

    async def download(
        self,
        file_id: str,
    ) -> bytes:

        file_info = await self._get_file_info(
            file_id
        )

        file_path = file_info.get(
            "file_path"
        )

        if not file_path:

            raise TelegramStorageError(
                "Local Bot API getFile response "
                "did not contain file_path."
            )

        # -------------------------------------------------
        # LOCAL BOT API BEHAVIOR
        # -------------------------------------------------
        #
        # The Local Bot API Server can return an
        # absolute local filesystem path.
        #
        # When that happens, read the file directly.
        #
        # -------------------------------------------------

        local_path = Path(
            file_path
        )

        if local_path.is_absolute():

            if not local_path.exists():

                raise TelegramTemporaryError(
                    "Telegram returned a local "
                    "file path, but the file "
                    "does not exist."
                )

            try:

                return local_path.read_bytes()

            except OSError as exc:

                raise TelegramTemporaryError(
                    f"Unable to read Telegram "
                    f"local file: {exc}"
                ) from exc

        # -------------------------------------------------
        # FALLBACK HTTP DOWNLOAD
        # -------------------------------------------------

        download_url = (
            f"{self.base_url}"
            f"/file/bot"
            f"{self.bot_token}/"
            f"{file_path}"
        )

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=30.0,
                read=1800.0,
                write=1800.0,
                pool=30.0,
            )
        ) as client:

            try:

                response = await client.get(
                    download_url
                )

            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as exc:

                raise TelegramTemporaryError(
                    f"Local Telegram download "
                    f"failed: {exc}"
                ) from exc

        if response.status_code != 200:

            raise TelegramTemporaryError(
                "Local Telegram file download "
                f"failed with HTTP "
                f"{response.status_code}."
            )

        return response.content

    # =====================================================
    # DELETE MESSAGE
    # =====================================================

    async def delete(
        self,
        chat_id: int,
        message_id: int,
    ) -> None:

        url = self._url(
            "deleteMessage"
        )

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                url,
                data={
                    "chat_id": str(
                        chat_id
                    ),
                    "message_id": str(
                        message_id
                    ),
                },
            )

        self._handle_response(
            response
        )
