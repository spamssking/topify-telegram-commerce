"""
tests/test_storage_system.py

Single-file test suite for the Telegram Cloud Storage system.

Run:

    pytest -v tests/test_storage_system.py

If pytest is not installed:

    uv pip install pytest pytest-asyncio

These tests use mocks and do NOT perform real Telegram uploads/deletes.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from app.services.file_service import FileService

import pytest


# ============================================================
# TELEGRAM STORAGE TESTS
# ============================================================


class TestTelegramStorage:
    """
    Tests TelegramStorage behavior without calling Telegram.
    """



    def test_extract_document(self):
        """
        Telegram returns a document.
        """

        from app.services.telegram_storage import TelegramStorage

        message = {
            "message_id": 10,
            "document": {
                "file_id": "DOCUMENT_FILE_ID",
                "file_unique_id": "DOCUMENT_UNIQUE_ID",
                "file_size": 12345,
                "file_name": "test.pdf",
            },
        }

        result = TelegramStorage.extract_file_info(
            message
        )

        assert result["type"] == "document"
        assert result["file_id"] == "DOCUMENT_FILE_ID"
        assert result["file_unique_id"] == "DOCUMENT_UNIQUE_ID"
        assert result["file_size"] == 12345

    def test_extract_audio(self):
        """
        Telegram returns audio instead of document.
        """

        from app.services.telegram_storage import TelegramStorage

        message = {
            "message_id": 11,
            "audio": {
                "file_id": "AUDIO_FILE_ID",
                "file_unique_id": "AUDIO_UNIQUE_ID",
                "file_size": 9491864,
                "file_name": "song.mp3",
                "mime_type": "audio/mpeg",
            },
        }

        result = TelegramStorage.extract_file_info(
            message
        )

        assert result["type"] == "audio"
        assert result["file_id"] == "AUDIO_FILE_ID"
        assert result["file_unique_id"] == "AUDIO_UNIQUE_ID"
        assert result["file_size"] == 9491864

    def test_extract_video(self):
        """
        Telegram returns video instead of document.
        """

        from app.services.telegram_storage import TelegramStorage

        message = {
            "message_id": 12,
            "video": {
                "file_id": "VIDEO_FILE_ID",
                "file_unique_id": "VIDEO_UNIQUE_ID",
                "file_size": 8190977,
                "file_name": "movie.mp4",
                "mime_type": "video/mp4",
            },
        }

        result = TelegramStorage.extract_file_info(
            message
        )

        assert result["type"] == "video"
        assert result["file_id"] == "VIDEO_FILE_ID"
        assert result["file_unique_id"] == "VIDEO_UNIQUE_ID"
        assert result["file_size"] == 8190977

    def test_extract_animation(self):
        """
        Telegram returns an animation.
        """

        from app.services.telegram_storage import TelegramStorage

        message = {
            "message_id": 13,
            "animation": {
                "file_id": "ANIMATION_FILE_ID",
                "file_unique_id": "ANIMATION_UNIQUE_ID",
                "file_size": 50000,
            },
        }

        result = TelegramStorage.extract_file_info(
            message
        )

        assert result["type"] == "animation"
        assert result["file_id"] == "ANIMATION_FILE_ID"

    def test_extract_photo(self):
        """
        Telegram returns photos as an array.
        The largest photo should be selected.
        """

        from app.services.telegram_storage import TelegramStorage

        message = {
            "message_id": 14,
            "photo": [
                {
                    "file_id": "SMALL_PHOTO",
                    "file_unique_id": "SMALL",
                    "file_size": 1000,
                    "width": 100,
                    "height": 100,
                },
                {
                    "file_id": "LARGE_PHOTO",
                    "file_unique_id": "LARGE",
                    "file_size": 5000,
                    "width": 1000,
                    "height": 1000,
                },
            ],
        }

        result = TelegramStorage.extract_file_info(
            message
        )

        assert result["type"] == "photo"
        assert result["file_id"] == "LARGE_PHOTO"
        assert result["file_size"] == 5000

    def test_extract_empty_response(self):
        """
        Telegram response contains no file.
        """

        from app.services.telegram_storage import TelegramStorage

        result = TelegramStorage.extract_file_info(
            {
                "message_id": 15,
                "chat": {
                    "id": -100123
                },
            }
        )

        assert result == {}

    def test_handle_successful_response(self):
        """
        Telegram API successful response.
        """

        from app.services.telegram_storage import TelegramStorage

        response = MagicMock()

        response.status_code = 200

        response.json.return_value = {
            "ok": True,
            "result": {
                "message_id": 100,
                "document": {
                    "file_id": "FILE_ID"
                },
            },
        }

        result = TelegramStorage._handle_response(
            TelegramStorage.__new__(
                TelegramStorage
            ),
            response,
        )

        assert result["message_id"] == 100
        assert result["document"]["file_id"] == "FILE_ID"

    def test_handle_invalid_json(self):
        """
        Telegram returns invalid JSON.
        """

        from app.services.telegram_storage import (
            TelegramStorage,
        )
        from app.services.telegram_errors import (
            TelegramTemporaryError,
        )

        response = MagicMock()

        response.status_code = 200
        response.json.side_effect = ValueError()

        with pytest.raises(
            TelegramTemporaryError
        ):

            TelegramStorage._handle_response(
                TelegramStorage.__new__(
                    TelegramStorage
                ),
                response,
            )

    @pytest.mark.asyncio
    async def test_delete_message_calls_telegram(self):

        """
        delete_message() should call Telegram deleteMessage.
        """

        from app.services.telegram_storage import TelegramStorage

        storage = TelegramStorage.__new__(
            TelegramStorage
        )

        storage.base_url = (
            "https://api.telegram.org/botTEST"
        )

        response = MagicMock()

        response.status_code = 200

        response.json.return_value = {
            "ok": True,
            "result": True,
        }

        client = MagicMock()

        client.post = AsyncMock(
            return_value=response
        )

        class FakeClient:

            async def __aenter__(self):
                return client

            async def __aexit__(
                self,
                exc_type,
                exc,
                tb,
            ):
                pass

        # Patch httpx client used by the module.
        import app.services.telegram_storage as module

        original_client = module.httpx.AsyncClient

        module.httpx.AsyncClient = FakeClient

        try:

            result = await storage.delete_message(
                chat_id=-100123456,
                message_id=123,
            )

        finally:

            module.httpx.AsyncClient = original_client

        assert result is True

        client.post.assert_awaited_once()

        kwargs = client.post.await_args.kwargs

        assert kwargs["data"]["chat_id"] == "-100123456"
        assert kwargs["data"]["message_id"] == "123"


# ============================================================
# FILE SERVICE TESTS
# ============================================================


class TestFileService:
    """
    Tests FileService using mocked repositories/services.
    """

    def create_service(self):

        from app.services.file_service import FileService

        db = MagicMock()

        service = FileService.__new__(
            FileService
        )

        service.db = db

        service.file_repository = MagicMock()
        service.chunk_repository = MagicMock()
        service.channel_repository = MagicMock()

        service.channel_selector = MagicMock()

        service.telegram = MagicMock()

        service.chunked_file_service = MagicMock()

        return service

    @pytest.mark.asyncio
    async def test_upload_audio_response_is_accepted(
        self,
    ):
        """
        Audio returned by Telegram must not be treated
        as an upload failure.
        """

        service = self.create_service()

        user = SimpleNamespace(
            id="USER_ID",
            storage_used=0,
            is_active=True,
            is_verified=True,
            plan=SimpleNamespace(
                code="FREE",
                max_file_size_bytes=50_000_000,
                storage_quota_bytes=1_000_000_000,
                name="FREE",
            ),
        )

        service.db.get.return_value = user

        upload = MagicMock()

        upload.filename = "song.mp3"
        upload.content_type = "audio/mpeg"

        upload.file = MagicMock()

        upload.file.tell.return_value = 1000

        upload.read = AsyncMock(
            return_value=b"a" * 1000
        )

        channel = SimpleNamespace(
            id="CHANNEL_ID",
            telegram_chat_id=-100123456,
        )

        service.channel_repository.get_active.return_value = [
            channel
        ]

        service.channel_selector.select.return_value = (
            channel
        )

        service.telegram.upload = AsyncMock(
            return_value={
                "message_id": 123,
                "audio": {
                    "file_id": "AUDIO_FILE_ID",
                    "file_unique_id": "AUDIO_UNIQUE_ID",
                    "file_size": 1000,
                },
            }
        )

        service.file_repository.create.side_effect = (
            lambda file: file
        )

        result = await service._upload_single_file(
            upload=upload,
            user=user,
            file_size=1000,
        )

        assert result.telegram_file_id == (
            "AUDIO_FILE_ID"
        )

        assert result.telegram_message_id == 123

        assert result.status == "STORED"

        assert result.is_chunked is False

    @pytest.mark.asyncio
    async def test_upload_video_response_is_accepted(
        self,
    ):
        """
        Video returned by Telegram must not be treated
        as an upload failure.
        """

        service = self.create_service()

        user = SimpleNamespace(
            id="USER_ID",
            storage_used=0,
        )

        upload = MagicMock()

        upload.filename = "movie.mp4"
        upload.content_type = "video/mp4"

        channel = SimpleNamespace(
            id="CHANNEL_ID",
            telegram_chat_id=-100123456,
        )

        service.channel_repository.get_active.return_value = [
            channel
        ]

        service.channel_selector.select.return_value = (
            channel
        )

        upload.read = AsyncMock(
            return_value=b"v" * 2000
        )

        service.telegram.upload = AsyncMock(
            return_value={
                "message_id": 456,
                "video": {
                    "file_id": "VIDEO_FILE_ID",
                    "file_unique_id": "VIDEO_UNIQUE_ID",
                    "file_size": 2000,
                },
            }
        )

        service.file_repository.create.side_effect = (
            lambda file: file
        )

        result = await service._upload_single_file(
            upload=upload,
            user=user,
            file_size=2000,
        )

        assert result.telegram_file_id == (
            "VIDEO_FILE_ID"
        )

        assert result.telegram_message_id == 456

        assert result.status == "STORED"

    @pytest.mark.asyncio
    async def test_upload_document_response_is_accepted(
        self,
    ):
        """
        Normal document upload.
        """

        service = self.create_service()

        user = SimpleNamespace(
            id="USER_ID",
            storage_used=0,
        )

        upload = MagicMock()

        upload.filename = "test.pdf"
        upload.content_type = "application/pdf"

        upload.read = AsyncMock(
            return_value=b"x" * 500
        )

        channel = SimpleNamespace(
            id="CHANNEL_ID",
            telegram_chat_id=-100123456,
        )

        service.channel_repository.get_active.return_value = [
            channel
        ]

        service.channel_selector.select.return_value = (
            channel
        )

        service.telegram.upload = AsyncMock(
            return_value={
                "message_id": 789,
                "document": {
                    "file_id": "DOCUMENT_FILE_ID",
                    "file_unique_id": "DOCUMENT_UNIQUE_ID",
                    "file_size": 500,
                },
            }
        )

        service.file_repository.create.side_effect = (
            lambda file: file
        )

        result = await service._upload_single_file(
            upload=upload,
            user=user,
            file_size=500,
        )

        assert result.telegram_file_id == (
            "DOCUMENT_FILE_ID"
        )

        assert result.telegram_message_id == 789

        assert result.status == "STORED"


# ============================================================
# DOWNLOAD TESTS
# ============================================================


class TestDownload:
    """
    Tests download and integrity checking.
    """

    @pytest.mark.asyncio
    async def test_download_normal_file(self):

        from app.services.file_service import FileService

        service = FileService.__new__(
            FileService
        )

        service.file_repository = MagicMock()
        service.telegram = MagicMock()
        service.chunked_file_service = MagicMock()

        original_data = b"hello telegram storage"

        import hashlib

        file_record = SimpleNamespace(
            id="FILE_ID",
            user_id="USER_ID",
            is_chunked=False,
            telegram_file_id="TELEGRAM_FILE_ID",
            sha256=hashlib.sha256(
                original_data
            ).hexdigest(),
            size=len(original_data),
        )

        service.file_repository.get_user_file.return_value = (
            file_record
        )

        service.telegram.get_file = AsyncMock(
            return_value=original_data
        )

        result_file, result_bytes = (
            await service.download(
                file_id="FILE_ID",
                user_id="USER_ID",
            )
        )

        assert result_file is file_record
        assert result_bytes == original_data

        service.telegram.get_file.assert_awaited_once_with(
            "TELEGRAM_FILE_ID"
        )

    @pytest.mark.asyncio
    async def test_download_detects_hash_corruption(self):

        from app.services.file_service import FileService

        service = FileService.__new__(
            FileService
        )

        service.file_repository = MagicMock()
        service.telegram = MagicMock()

        service.chunked_file_service = MagicMock()

        file_record = SimpleNamespace(
            id="FILE_ID",
            user_id="USER_ID",
            is_chunked=False,
            telegram_file_id="TELEGRAM_FILE_ID",
            sha256="incorrect_hash",
            size=5,
        )

        service.file_repository.get_user_file.return_value = (
            file_record
        )

        service.telegram.get_file = AsyncMock(
            return_value=b"hello"
        )

        with pytest.raises(
            RuntimeError,
            match="integrity check failed",
        ):

            await service.download(
                file_id="FILE_ID",
                user_id="USER_ID",
            )

    @pytest.mark.asyncio
    async def test_download_detects_size_corruption(self):

        from app.services.file_service import FileService

        service = FileService.__new__(
            FileService
        )

        service.file_repository = MagicMock()
        service.telegram = MagicMock()

        service.chunked_file_service = MagicMock()

        data = b"hello"

        import hashlib

        file_record = SimpleNamespace(
            id="FILE_ID",
            user_id="USER_ID",
            is_chunked=False,
            telegram_file_id="TELEGRAM_FILE_ID",
            sha256=hashlib.sha256(
                data
            ).hexdigest(),
            size=999,
        )

        service.file_repository.get_user_file.return_value = (
            file_record
        )

        service.telegram.get_file = AsyncMock(
            return_value=data
        )

        with pytest.raises(
            RuntimeError,
            match="size does not match",
        ):

            await service.download(
                file_id="FILE_ID",
                user_id="USER_ID",
            )


# ============================================================
# DELETE TESTS
# ============================================================


class TestDelete:
    """
    Tests deletion of normal files and chunked files.
    """

    @pytest.mark.asyncio
    async def test_delete_normal_file(self):

        from app.services.file_service import FileService

        service = FileService.__new__(
            FileService
        )

        service.file_repository = MagicMock()
        service.chunk_repository = MagicMock()
        service.channel_repository = MagicMock()
        service.telegram = MagicMock()

        service.db = MagicMock()

        file_record = SimpleNamespace(
            id="FILE_ID",
            user_id="USER_ID",
            is_chunked=False,
            storage_channel_id="CHANNEL_ID",
            telegram_message_id=123,
            size=1000,
            deleted_at=None,
            status="STORED",
        )

        channel = SimpleNamespace(
            id="CHANNEL_ID",
            telegram_chat_id=-100123456,
        )

        user = SimpleNamespace(
            id="USER_ID",
            storage_used=5000,
        )

        service.file_repository.get_user_file.return_value = (
            file_record
        )

        service.channel_repository.get_by_id.return_value = (
            channel
        )

        service.db.get.return_value = user

        service.telegram.delete_message = AsyncMock(
            return_value=True
        )

        await service.delete(
            file_id="FILE_ID",
            user_id="USER_ID",
        )

        service.telegram.delete_message.assert_awaited_once_with(
            chat_id=-100123456,
            message_id=123,
        )

        assert file_record.status == "DELETED"

        assert file_record.deleted_at is not None

        assert user.storage_used == 4000

        service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_chunked_file(self):

        from app.services.file_service import FileService

        service = FileService.__new__(
            FileService
        )

        service.file_repository = MagicMock()
        service.chunk_repository = MagicMock()
        service.channel_repository = MagicMock()
        service.telegram = MagicMock()

        service.db = MagicMock()

        file_record = SimpleNamespace(
            id="FILE_ID",
            user_id="USER_ID",
            is_chunked=True,
            size=3000,
            deleted_at=None,
            status="STORED",
        )

        chunk1 = SimpleNamespace(
            id="CHUNK_1",
            storage_channel_id="CHANNEL_1",
            telegram_message_id=101,
        )

        chunk2 = SimpleNamespace(
            id="CHUNK_2",
            storage_channel_id="CHANNEL_2",
            telegram_message_id=202,
        )

        channel1 = SimpleNamespace(
            id="CHANNEL_1",
            telegram_chat_id=-100111111,
        )

        channel2 = SimpleNamespace(
            id="CHANNEL_2",
            telegram_chat_id=-100222222,
        )

        user = SimpleNamespace(
            id="USER_ID",
            storage_used=5000,
        )

        service.file_repository.get_user_file.return_value = (
            file_record
        )

        service.chunk_repository.get_by_file.return_value = [
            chunk1,
            chunk2,
        ]

        def get_channel(channel_id):

            if channel_id == "CHANNEL_1":
                return channel1

            if channel_id == "CHANNEL_2":
                return channel2

            return None

        service.channel_repository.get_by_id.side_effect = (
            get_channel
        )

        service.db.get.return_value = user

        service.telegram.delete_message = AsyncMock(
            return_value=True
        )

        await service.delete(
            file_id="FILE_ID",
            user_id="USER_ID",
        )

        assert (
            service.telegram.delete_message.await_count
            == 2
        )

        service.telegram.delete_message.assert_any_await(
            chat_id=-100111111,
            message_id=101,
        )

        service.telegram.delete_message.assert_any_await(
            chat_id=-100222222,
            message_id=202,
        )

        assert file_record.status == "DELETED"

        assert user.storage_used == 2000

        service.db.commit.assert_called_once()


# ============================================================
# MODEL TESTS
# ============================================================


class TestFileModel:

    def test_file_model_has_required_fields(self):

        from app.models.file import File

        table_columns = {
            column.name
            for column in File.__table__.columns
        }

        required = {
            "id",
            "user_id",
            "storage_channel_id",
            "telegram_message_id",
            "telegram_file_id",
            "storage_backend",
            "name",
            "mime_type",
            "size",
            "is_chunked",
            "chunk_count",
            "sha256",
            "status",
            "created_at",
            "updated_at",
            "deleted_at",
        }

        assert required.issubset(
            table_columns
        )

    def test_telegram_fields_are_not_duplicated(self):

        from app.models.file import File

        message_id_columns = [
            column
            for column in File.__table__.columns
            if column.name == "telegram_message_id"
        ]

        file_id_columns = [
            column
            for column in File.__table__.columns
            if column.name == "telegram_file_id"
        ]

        assert len(message_id_columns) == 1

        assert len(file_id_columns) == 1


# ============================================================
# BASIC SYSTEM TEST
# ============================================================


def test_python_environment():

    """
    Very basic test to make sure pytest is actually
    executing inside the project environment.
    """

    import sys

    assert sys.version_info >= (
        3,
        10,
    )

def test_pagination():
    from app.services.file_service import FileService

    service = FileService.__new__(FileService)

    service.file_repository = MagicMock()

    service.file_repository.list_files.return_value = {
        "items": [],
        "total": 0,
    }

    result = service.list_files(
        user_id="USER_ID",
        page=1,
        page_size=10,
    )

    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["total"] >= 0
    assert isinstance(result["items"], list)


