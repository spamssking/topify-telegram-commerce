from app.core.database import SessionLocal
from app.models.user import User


TEST_USER_ID = (
    "00000000-0000-0000-0000-000000000001"
)


def main():

    db = SessionLocal()

    existing = db.get(
        User,
        TEST_USER_ID,
    )

    if existing:
        print("Test user already exists.")
        return

    user = User(
        id=TEST_USER_ID,
        email="test@example.com",
    )

    db.add(user)
    db.commit()

    print("Test user created.")


if __name__ == "__main__":
    main()
