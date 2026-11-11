import asyncio

from app.services.telegram_storage import TelegramStorage


async def main():
    telegram = TelegramStorage()

    result = await telegram.send_test_message(
        chat_id=-1003712495667,
        text="Telegram storage backend test successful!",
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
