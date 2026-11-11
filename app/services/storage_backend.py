# app/services/storage_backend.py

from abc import ABC, abstractmethod


class StorageBackend(ABC):

    @abstractmethod
    async def upload(
        self,
        *,
        chat_id: int,
        file_path: str,
        filename: str,
    ) -> dict:
        """
        Upload a local file to storage.
        """
        raise NotImplementedError

    @abstractmethod
    async def download(
        self,
        file_id: str,
    ) -> bytes:
        """
        Download a stored file.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        *,
        chat_id: int,
        message_id: int,
    ) -> None:
        """
        Delete a stored message/file.
        """
        raise NotImplementedError
