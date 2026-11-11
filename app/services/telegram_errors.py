class TelegramStorageError(Exception):
    """Base Telegram storage exception."""


class TelegramRateLimitError(
    TelegramStorageError
):

    def __init__(
        self,
        retry_after: int,
        message: str = "Telegram rate limit.",
    ):
        self.retry_after = retry_after

        super().__init__(message)


class TelegramTemporaryError(
    TelegramStorageError
):
    """Temporary error that should be retried."""


class TelegramPermanentError(
    TelegramStorageError
):
    """Permanent error that should not be retried."""
