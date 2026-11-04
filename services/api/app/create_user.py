
import asyncio
import getpass

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from app.core.security import hash_password
from app.db.mongo import (
    close_mongodb_connection,
    connect_to_mongodb,
    get_database,
)


async def main() -> None:
    email = input("Administrator email: ").strip().lower()

    if (
        not email
        or len(email) > 254
        or "@" not in email
        or email.startswith("@")
        or email.endswith("@")
    ):
        raise SystemExit("Enter a valid email address.")

    password = getpass.getpass("New password (hidden): ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        raise SystemExit("Passwords do not match.")

    if len(password) < 12 or len(password) > 128:
        raise SystemExit("Password must contain 12–128 characters.")

    if password.strip() != password:
        raise SystemExit("Password cannot start or end with whitespace.")

    await connect_to_mongodb()

    try:
        database = get_database()

        await database.users.create_index(
            [("email", ASCENDING)],
            unique=True,
            name="unique_user_email",
        )

        existing_admin = await database.users.find_one(
            {"role": "admin", "is_active": True},
            {"_id": 1},
        )

        if existing_admin:
            raise SystemExit(
                "An active administrator already exists. "
                "Use the approved admin-management flow."
            )

        await database.users.insert_one(
            {
                "email": email,
                "password_hash": hash_password(password),
                "role": "admin",
                "is_active": True,
            }
        )

        print("Administrator account created successfully.")

    except DuplicateKeyError:
        raise SystemExit("An account with that email already exists.") from None
    finally:
        await close_mongodb_connection()


if __name__ == "__main__":
    asyncio.run(main())
