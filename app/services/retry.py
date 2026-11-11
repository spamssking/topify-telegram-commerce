import asyncio
import random


async def retry_async(
    operation,
    *,
    max_attempts: int = 10,
    base_delay: float = 2.0,
    max_delay: float = 300.0,
):

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        try:
            return await operation()

        except Exception as exc:

            last_error = exc

            if attempt >= max_attempts:
                raise

            delay = min(
                max_delay,
                base_delay * (
                    2 ** (attempt - 1)
                ),
            )

            # Small jitter prevents many workers
            # retrying at exactly the same time.
            delay += random.uniform(
                0,
                1,
            )

            await asyncio.sleep(
                delay
            )

    raise last_error
