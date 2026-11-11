import asyncio
import httpx

from app.core.config import settings


async def main():

    url = (
        f"https://api.telegram.org/bot"
        f"{settings.telegram_cloud_bot_token}/getUpdates"
    )

    async with httpx.AsyncClient() as client:

        response = await client.get(url)

        print("HTTP status:", response.status_code)

        data = response.json()

        print(data)


if __name__ == "__main__":
    asyncio.run(main())
