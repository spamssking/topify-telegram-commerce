import random

from app.models.storage_channel import StorageChannel


class NoStorageChannelAvailable(Exception):
    pass


class ChannelSelector:

    def select(
        self,
        channels: list[StorageChannel],
    ) -> StorageChannel:

        if not channels:
            raise NoStorageChannelAvailable(
                "No active Telegram storage channels available."
            )

        return random.choice(channels)
