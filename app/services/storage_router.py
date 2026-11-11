# app/services/storage_router.py

from app.services.local_telegram_storage import (
    LocalTelegramStorage,
)

from app.services.telegram_storage import (
    TelegramStorage,
)


class StorageRouter:

    def __init__(self):

        self._local = (
            LocalTelegramStorage()
        )

        self._cloud = (
            TelegramStorage()
        )

    # =====================================================
    # PRIMARY
    # =====================================================

    def primary(self):

        return self._local

    # =====================================================
    # FALLBACK
    # =====================================================

    def fallback(self):

        return self._cloud

    # =====================================================
    # NAMED ACCESS
    # =====================================================

    def local(self):

        return self._local

    def cloud(self):

        return self._cloud
