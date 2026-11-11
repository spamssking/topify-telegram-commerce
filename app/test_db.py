from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


def main():
    print("Database URL:")
    print(settings.database_url)

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Database connection successful!")
            print("Result:", result.scalar())

    except Exception as e:
        print("Database connection FAILED!")
        print(type(e).__name__)
        print(e)


if __name__ == "__main__":
    main()
