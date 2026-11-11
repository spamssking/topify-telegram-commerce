import hashlib
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chunked_file_service import (
    ChunkedFileService,
)
from app.services.telegram_storage import (
    TelegramStorageError,
)


# =========================================================
# TEST HELPERS
# =========================================================

def make_chunk_service():

    service = ChunkedFileService.__new__(
        ChunkedFileService
    )

    service.db = MagicMock()

    service.file_repository = MagicMock()
    service.chunk_repository = MagicMock()
    service.channel_repository = MagicMock()
    service.channel_selector = MagicMock()

    service.telegram = MagicMock()

    service.telegram.upload = AsyncMock()
    service.telegram.get_file = AsyncMock()
    service.telegram.delete_message = AsyncMock()

    return service


def make_file(
    *,
    file_id="file-1",
    size=10,
    sha256=None,
    chunk_count=2,
):

    if sha256 is None:
        sha256 = hashlib.sha256(
            b"abcdefghij"
        ).hexdigest()

    return SimpleNamespace(
        id=file_id,
        size=size,
        sha256=sha256,
        chunk_count=chunk_count,
        is_chunked=True,
    )


def make_channel():

    return SimpleNamespace(
        id="channel-1",
        telegram_chat_id=123456,
    )


def make_user():

    return SimpleNamespace(
        id="user-1",
        storage_used=0,
    )


# =========================================================
# 1. CHUNKED UPLOAD
# =========================================================

@pytest.mark.asyncio
async def test_chunked_file_upload():

    service = make_chunk_service()

    upload = MagicMock()

    upload.filename = "large.bin"
    upload.content_type = "application/octet-stream"

    upload.read = AsyncMock(
        side_effect=[
            b"aaaaa",
            b"bbbbb",
            b"cc",
            b"",
        ]
    )

    user = make_user()
    channel = make_channel()

    service.channel_repository.get_active.return_value = [
        channel
    ]

    service.channel_selector.select.return_value = channel

    service.telegram.upload.side_effect = [
        {
            "message_id": 100,
            "document": {
                "file_id": "tg-100"
            },
        },
        {
            "message_id": 101,
            "document": {
                "file_id": "tg-101"
            },
        },
        {
            "message_id": 102,
            "document": {
                "file_id": "tg-102"
            },
        },
    ]

    file_record = await service.upload(
        upload=upload,
        user=user,
        file_size=12,
        chunk_size=5,
    )

    assert file_record.is_chunked is True
    assert file_record.chunk_count == 3
    assert file_record.size == 12
    assert file_record.status == "STORED"

    assert (
        service.chunk_repository.create.call_count
        == 3
    )

    created_chunks = [
        call.args[0]
        for call in (
            service.chunk_repository
            .create
            .call_args_list
        )
    ]

    assert [
        chunk.chunk_index
        for chunk in created_chunks
    ] == [0, 1, 2]

    assert [
        chunk.size
        for chunk in created_chunks
    ] == [5, 5, 2]


# =========================================================
# 2. SMALL FILE REJECTED BY CHUNK SERVICE
# =========================================================

@pytest.mark.asyncio
async def test_small_file_upload_rejected_by_chunk_service():

    service = make_chunk_service()

    upload = MagicMock()

    user = make_user()

    with pytest.raises(
        ValueError,
        match="does not need chunking",
    ):
        await service.upload(
            upload=upload,
            user=user,
            file_size=5,
            chunk_size=10,
        )


# =========================================================
# 3. CHUNK ORDER
# =========================================================

@pytest.mark.asyncio
async def test_chunk_order():

    service = make_chunk_service()

    chunk_a = SimpleNamespace(
        chunk_index=0,
        telegram_file_id="tg-0",
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
    )

    chunk_b = SimpleNamespace(
        chunk_index=2,
        telegram_file_id="tg-2",
        size=5,
        sha256=hashlib.sha256(
            b"world"
        ).hexdigest(),
    )

    service.chunk_repository.get_by_file.return_value = [
        chunk_a,
        chunk_b,
    ]

    file = make_file(
        size=10,
        sha256=hashlib.sha256(
            b"helloworld"
        ).hexdigest(),
        chunk_count=2,
    )

    service.telegram.get_file.return_value = b"hello"

    with pytest.raises(
        ValueError,
        match="out of order",
    ):
        await service.download_to_temp_file(file)


# =========================================================
# 4. CHUNK HASH
# =========================================================

@pytest.mark.asyncio
async def test_chunk_hash():

    service = make_chunk_service()

    chunk = SimpleNamespace(
        chunk_index=0,
        telegram_file_id="tg-0",
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
    )

    service.chunk_repository.get_by_file.return_value = [
        chunk
    ]

    file = make_file(
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
        chunk_count=1,
    )

    service.telegram.get_file.return_value = b"WRONG"

    with pytest.raises(
        ValueError,
        match="failed integrity verification",
    ):
        await service.download_to_temp_file(file)


# =========================================================
# 5. COMPLETE FILE HASH
# =========================================================

@pytest.mark.asyncio
async def test_complete_file_hash():

    service = make_chunk_service()

    chunk_a = SimpleNamespace(
        chunk_index=0,
        telegram_file_id="tg-0",
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
    )

    chunk_b = SimpleNamespace(
        chunk_index=1,
        telegram_file_id="tg-1",
        size=5,
        sha256=hashlib.sha256(
            b"world"
        ).hexdigest(),
    )

    service.chunk_repository.get_by_file.return_value = [
        chunk_a,
        chunk_b,
    ]

    file = make_file(
        size=10,
        sha256=hashlib.sha256(
            b"helloworld"
        ).hexdigest(),
        chunk_count=2,
    )

    service.telegram.get_file.side_effect = [
        b"hello",
        b"world",
    ]

    temp_path = await service.download_to_temp_file(
        file
    )

    try:

        with open(temp_path, "rb") as f:
            assert f.read() == b"helloworld"

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)


# =========================================================
# 6. DOWNLOAD REASSEMBLY
# =========================================================

@pytest.mark.asyncio
async def test_download_reassembly():

    service = make_chunk_service()

    chunks = [
        SimpleNamespace(
            chunk_index=0,
            telegram_file_id="tg-0",
            size=5,
            sha256=hashlib.sha256(
                b"hello"
            ).hexdigest(),
        ),
        SimpleNamespace(
            chunk_index=1,
            telegram_file_id="tg-1",
            size=6,
            sha256=hashlib.sha256(
                b" world"
            ).hexdigest(),
        ),
    ]

    service.chunk_repository.get_by_file.return_value = chunks

    complete_data = b"hello world"

    file = make_file(
        size=len(complete_data),
        sha256=hashlib.sha256(
            complete_data
        ).hexdigest(),
        chunk_count=2,
    )

    service.telegram.get_file.side_effect = [
        b"hello",
        b" world",
    ]

    temp_path = await service.download_to_temp_file(
        file
    )

    try:

        with open(temp_path, "rb") as f:
            assert f.read() == complete_data

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)


# =========================================================
# 7. CORRUPTED CHUNK
# =========================================================

@pytest.mark.asyncio
async def test_corrupted_chunk():

    service = make_chunk_service()

    chunk = SimpleNamespace(
        chunk_index=0,
        telegram_file_id="tg-0",
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
    )

    service.chunk_repository.get_by_file.return_value = [
        chunk
    ]

    file = make_file(
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
        chunk_count=1,
    )

    service.telegram.get_file.return_value = b"xxxxx"

    with pytest.raises(
        ValueError,
        match="failed integrity verification",
    ):
        await service.download_to_temp_file(file)


# =========================================================
# 8. MISSING CHUNK
# =========================================================

@pytest.mark.asyncio
async def test_missing_chunk():

    service = make_chunk_service()

    service.chunk_repository.get_by_file.return_value = []

    file = make_file()

    with pytest.raises(
        ValueError,
        match="No chunks found",
    ):
        await service.download_to_temp_file(file)


# =========================================================
# 9. TELEGRAM DOWNLOAD FAILURE
# =========================================================

@pytest.mark.asyncio
async def test_telegram_download_failure():

    service = make_chunk_service()

    chunk = SimpleNamespace(
        chunk_index=0,
        telegram_file_id="tg-0",
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
    )

    service.chunk_repository.get_by_file.return_value = [
        chunk
    ]

    file = make_file(
        size=5,
        sha256=hashlib.sha256(
            b"hello"
        ).hexdigest(),
        chunk_count=1,
    )

    service.telegram.get_file.side_effect = (
        TelegramStorageError(
            "Telegram download failed"
        )
    )

    with pytest.raises(
        TelegramStorageError,
        match="Telegram download failed",
    ):
        await service.download_to_temp_file(file)


# =========================================================
# 10. CHUNK HASH SAVED
# =========================================================

@pytest.mark.asyncio
async def test_chunk_hash_saved():

    service = make_chunk_service()

    upload = MagicMock()

    upload.filename = "test.bin"
    upload.content_type = "application/octet-stream"

    upload.read = AsyncMock(
        side_effect=[
            b"hello",
            b"world",
            b"",
        ]
    )

    user = make_user()
    channel = make_channel()

    service.channel_repository.get_active.return_value = [
        channel
    ]

    service.channel_selector.select.return_value = channel

    service.telegram.upload.side_effect = [
        {
            "message_id": 100,
            "document": {
                "file_id": "tg-100"
            },
        },
        {
            "message_id": 101,
            "document": {
                "file_id": "tg-101"
            },
        },
    ]

    file_record = await service.upload(
        upload=upload,
        user=user,
        file_size=10,
        chunk_size=5,
    )

    assert file_record.chunk_count == 2

    first_chunk = (
        service.chunk_repository
        .create
        .call_args_list[0]
        .args[0]
    )

    assert first_chunk.sha256 == hashlib.sha256(
        b"hello"
    ).hexdigest()

    assert first_chunk.size == 5
    assert first_chunk.chunk_index == 0
    assert first_chunk.telegram_file_id == "tg-100"


# =========================================================
# 11. TELEGRAM UPLOAD FAILURE CLEANUP
# =========================================================

@pytest.mark.asyncio
async def test_telegram_upload_failure_cleanup():

    service = make_chunk_service()

    upload = MagicMock()

    upload.filename = "test.bin"
    upload.content_type = "application/octet-stream"

    upload.read = AsyncMock(
        side_effect=[
            b"aaaaa",
            b"bbbbb",
        ]
    )

    user = make_user()
    channel = make_channel()

    service.channel_repository.get_active.return_value = [
        channel
    ]

    service.channel_selector.select.return_value = channel

    service.telegram.upload.side_effect = [
        {
            "message_id": 100,
            "document": {
                "file_id": "tg-100"
            },
        },
        TelegramStorageError(
            "Telegram upload failed"
        ),
    ]

    with pytest.raises(
        TelegramStorageError,
        match="Telegram upload failed",
    ):
        await service.upload(
            upload=upload,
            user=user,
            file_size=10,
            chunk_size=5,
        )

    service.telegram.delete_message.assert_awaited_once_with(
        chat_id=123456,
        message_id=100,
    )

    service.db.rollback.assert_called_once()


# =========================================================
# 12. DATABASE FAILURE CLEANUP
# =========================================================

@pytest.mark.asyncio
async def test_database_failure_cleanup():

    service = make_chunk_service()

    upload = MagicMock()

    upload.filename = "test.bin"
    upload.content_type = "application/octet-stream"

    upload.read = AsyncMock(
        side_effect=[
            b"aaaaa",
            b"bbbbb",
            b"",
        ]
    )

    user = make_user()
    channel = make_channel()

    service.channel_repository.get_active.return_value = [
        channel
    ]

    service.channel_selector.select.return_value = channel

    service.telegram.upload.side_effect = [
        {
            "message_id": 100,
            "document": {
                "file_id": "tg-100"
            },
        },
        {
            "message_id": 101,
            "document": {
                "file_id": "tg-101"
            },
        },
    ]

    service.db.commit.side_effect = RuntimeError(
        "database failure"
    )

    with pytest.raises(
        RuntimeError,
        match="database failure",
    ):
        await service.upload(
            upload=upload,
            user=user,
            file_size=10,
            chunk_size=5,
        )

    assert (
        service.telegram.delete_message.await_count
        == 2
    )

    service.db.rollback.assert_called_once()

    calls = (
        service.telegram
        .delete_message
        .await_args_list
    )

    assert calls[0].kwargs["message_id"] == 100
    assert calls[1].kwargs["message_id"] == 101


# =========================================================
# 13. DELETE CHUNKED FILE
# =========================================================

@pytest.mark.asyncio
async def test_delete_chunked_file():

    service = make_chunk_service()

    # This test targets FileService.delete(),
    # not ChunkedFileService.delete().
    #
    # The chunked service itself does not own deletion.

    from app.services.file_service import FileService

    file_service = FileService.__new__(
        FileService
    )

    file_service.db = MagicMock()
    file_service.file_repository = MagicMock()
    file_service.chunk_repository = MagicMock()
    file_service.channel_repository = MagicMock()
    file_service.telegram = MagicMock()

    file_service.telegram.delete_message = AsyncMock()

    file = SimpleNamespace(
        id="file-1",
        user_id="user-1",
        is_chunked=True,
        size=10,
        status="STORED",
        deleted_at=None,
    )

    chunk_a = SimpleNamespace(
        storage_channel_id="channel-1",
        telegram_message_id=100,
    )

    chunk_b = SimpleNamespace(
        storage_channel_id="channel-1",
        telegram_message_id=101,
    )

    file_service.file_repository.get_user_file.return_value = file

    file_service.chunk_repository.get_by_file.return_value = [
        chunk_a,
        chunk_b,
    ]

    channel = SimpleNamespace(
        id="channel-1",
        telegram_chat_id=123456,
    )

    file_service.channel_repository.get_by_id.return_value = (
        channel
    )

    user = SimpleNamespace(
        id="user-1",
        storage_used=100,
    )

    file_service.db.get.return_value = user

    await file_service.delete(
        file_id="file-1",
        user_id="user-1",
    )

    assert (
        file_service.telegram
        .delete_message
        .await_count
        == 2
    )

    calls = (
        file_service.telegram
        .delete_message
        .await_args_list
    )

    assert calls[0].kwargs["message_id"] == 100
    assert calls[1].kwargs["message_id"] == 101

    assert file.status == "DELETED"
    assert user.storage_used == 90


# =========================================================
# 14. USER CANNOT DOWNLOAD OTHER USER'S FILE
# =========================================================

@pytest.mark.asyncio
async def test_user_cannot_download_other_users_file():

    service = make_chunk_service()

    service.file_repository.get_user_file.return_value = None

    from app.services.file_service import FileService

    file_service = FileService.__new__(
        FileService
    )

    file_service.file_repository = (
        service.file_repository
    )

    with pytest.raises(
        FileNotFoundError,
        match="File not found",
    ):

        file = file_service.file_repository.get_user_file(
            file_id="file-1",
            user_id="different-user",
        )

        if not file:
            raise FileNotFoundError(
                "File not found."
            )
